// SPDX-License-Identifier: MPL-2.0
//
// mgba_capture: native libmgba-driven capture tool for the Korean LeafGreen
// text engine. Loads the ROM, attaches a custom debugger module, sets a
// software breakpoint at the per-glyph render entry (0x080062B4 Thumb),
// auto-presses A to advance dialog, and on each breakpoint hit captures
// (page, idx) decoded from r0 plus periodic VRAM tile-group fingerprints.
// Output: JSON to --out (default .moneo-artifacts/capture.json).
//
// Built against mGBA HEAD's debugger-module API (post-0.10.x split between
// `struct mDebugger` and per-client `struct mDebuggerModule`).

#define ENABLE_VFS

#include <mgba/core/core.h>
#include <mgba/core/config.h>
#include <mgba/core/log.h>
#include <mgba/gba/core.h>
#include <mgba/gba/interface.h>
#include <mgba/debugger/debugger.h>
#include <mgba/internal/arm/arm.h>
#include <mgba-util/vfs.h>
#include <mgba-util/common.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <signal.h>
#include <getopt.h>
#include <fcntl.h>
#include <unistd.h>

// ---- Tiny SHA-256 (public domain) ------------------------------------------
typedef struct { uint32_t s[8]; uint64_t bits; uint8_t buf[64]; size_t blen; } SHA256;
static const uint32_t SHA_K[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2,
};
static void sha256_init(SHA256* c){
    static const uint32_t I[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    memcpy(c->s,I,sizeof I); c->bits=0; c->blen=0;
}
static uint32_t rr(uint32_t x,int n){return(x>>n)|(x<<(32-n));}
static void sha256_block(SHA256*c,const uint8_t*p){
    uint32_t w[64];
    for(int i=0;i<16;i++) w[i]=(uint32_t)p[i*4]<<24|(uint32_t)p[i*4+1]<<16|(uint32_t)p[i*4+2]<<8|p[i*4+3];
    for(int i=16;i<64;i++){uint32_t s0=rr(w[i-15],7)^rr(w[i-15],18)^(w[i-15]>>3);uint32_t s1=rr(w[i-2],17)^rr(w[i-2],19)^(w[i-2]>>10);w[i]=w[i-16]+s0+w[i-7]+s1;}
    uint32_t a=c->s[0],b=c->s[1],d=c->s[2],e=c->s[3],f=c->s[4],g=c->s[5],h=c->s[6],i2=c->s[7];
    for(int j=0;j<64;j++){uint32_t S1=rr(f,6)^rr(f,11)^rr(f,25);uint32_t ch=(f&g)^(~f&h);uint32_t t1=i2+S1+ch+SHA_K[j]+w[j];uint32_t S0=rr(a,2)^rr(a,13)^rr(a,22);uint32_t mj=(a&b)^(a&d)^(b&d);uint32_t t2=S0+mj;i2=h;h=g;g=f;f=e+t1;e=d;d=b;b=a;a=t1+t2;}
    c->s[0]+=a;c->s[1]+=b;c->s[2]+=d;c->s[3]+=e;c->s[4]+=f;c->s[5]+=g;c->s[6]+=h;c->s[7]+=i2;
}
static void sha256_update(SHA256*c,const void*data,size_t n){const uint8_t*p=(const uint8_t*)data;c->bits+=n*8;while(n){size_t take=64-c->blen;if(take>n)take=n;memcpy(c->buf+c->blen,p,take);c->blen+=take;p+=take;n-=take;if(c->blen==64){sha256_block(c,c->buf);c->blen=0;}}}
static void sha256_final(SHA256*c,uint8_t out[32]){c->buf[c->blen++]=0x80;if(c->blen>56){memset(c->buf+c->blen,0,64-c->blen);sha256_block(c,c->buf);c->blen=0;}memset(c->buf+c->blen,0,56-c->blen);uint64_t bits=c->bits;for(int i=0;i<8;i++)c->buf[63-i]=(uint8_t)(bits>>(i*8));sha256_block(c,c->buf);for(int i=0;i<8;i++){out[i*4]=(uint8_t)(c->s[i]>>24);out[i*4+1]=(uint8_t)(c->s[i]>>16);out[i*4+2]=(uint8_t)(c->s[i]>>8);out[i*4+3]=(uint8_t)c->s[i];}}

// ---- Globals ---------------------------------------------------------------
static volatile int g_stop = 0;
static void on_sigint(int s) { (void)s; g_stop = 1; }

typedef struct { uint64_t frame; uint32_t pc; uint8_t page; uint16_t idx; uint32_t r0; } Token;
typedef struct { uint64_t frame; int line; int pos; uint16_t tiles[4]; char fps[4][17]; } Group;

#define MAX_TOKENS 200000
#define MAX_GROUPS 50000
static Token g_tokens[MAX_TOKENS]; static size_t g_ntok = 0;
static Group g_groups[MAX_GROUPS]; static size_t g_ngrp = 0;

static struct mCore* g_core = NULL;
static struct mDebugger     g_debugger;
static struct mDebuggerModule g_module;
static int                  g_hits = 0;

// ---- Module callbacks (HEAD API) -------------------------------------------
static void mod_init(struct mDebuggerModule* m)   { (void)m; }
static void mod_deinit(struct mDebuggerModule* m) { (void)m; }
static void mod_paused(struct mDebuggerModule* m, int32_t timeoutMs) {
    (void)timeoutMs; m->isPaused = false;
}
static void mod_update(struct mDebuggerModule* m) { (void)m; }
static void mod_custom(struct mDebuggerModule* m) { (void)m; }
static void mod_interrupt(struct mDebuggerModule* m) { (void)m; }

static void mod_entered(struct mDebuggerModule* m,
                        enum mDebuggerEntryReason reason,
                        struct mDebuggerEntryInfo* info) {
    g_hits++;
    if (reason == DEBUGGER_ENTER_BREAKPOINT) {
        struct ARMCore* cpu = (struct ARMCore*)g_core->cpu;
        uint32_t r0 = (uint32_t)cpu->gprs[0];
        uint32_t pc = (uint32_t)cpu->gprs[15];
        uint8_t  page = (uint8_t)(r0 & 0xF);
        uint16_t idx  = (uint16_t)((r0 >> 4) & 0xFFF);
        if (g_ntok < MAX_TOKENS) {
            uint64_t fr = g_core->frameCounter(g_core);
            g_tokens[g_ntok++] = (Token){fr, pc, page, idx, r0};
        }
    }
    (void)info;
    m->isPaused = false;
    m->p->state = DEBUGGER_RUNNING;
}

// ---- VRAM fingerprinting ---------------------------------------------------
#define VRAM_BASE      0x06000000u
#define VRAM_BG_BYTES  0x10000u
#define SB31_OFFSET    (31u * 2048u)
#define MAP_COLS       32
#define CHARBLOCK_SIZE 16384u
#define TILE_BYTES     32u
static const int TEXT_ROW_TOPS[] = {3, 5, 7, 10, 12, 15, 17};
#define TEXT_ROWS_N    7
#define CHARS_PER_LINE 11

static uint16_t sb31_tile(const uint8_t* vram, int row, int col) {
    size_t off = (size_t)SB31_OFFSET + (size_t)(row * MAP_COLS + col) * 2;
    if (off + 2 > VRAM_BG_BYTES) return 0;
    return (uint16_t)((vram[off] | (vram[off+1] << 8)) & 0x3FF);
}
static void fp16(const uint8_t* in128, char out[17]) {
    SHA256 c; sha256_init(&c); sha256_update(&c, in128, 128);
    uint8_t d[32]; sha256_final(&c, d);
    for (int i = 0; i < 8; i++) sprintf(out + i*2, "%02x", d[i]);
    out[16] = 0;
}
static void capture_groups(uint64_t frame) {
    static uint8_t vram[VRAM_BG_BYTES];
    for (size_t i = 0; i < VRAM_BG_BYTES; i++) {
        vram[i] = (uint8_t)g_core->busRead8(g_core, (uint32_t)(VRAM_BASE + i));
    }
    for (int li = 0; li < TEXT_ROWS_N; li++) {
        int top = TEXT_ROW_TOPS[li];
        int start = -1;
        for (int c = 0; c < MAP_COLS; c++) {
            if (sb31_tile(vram, top, c) != 0) { start = c; break; }
        }
        if (start < 0) continue;
        for (int n = 0; n < CHARS_PER_LINE; n++) {
            int col = start + n*2;
            if (col + 1 >= MAP_COLS) break;
            uint16_t tl = sb31_tile(vram, top,   col);
            uint16_t tr = sb31_tile(vram, top,   col+1);
            uint16_t bl = sb31_tile(vram, top+1, col);
            uint16_t br = sb31_tile(vram, top+1, col+1);
            if (!tl && !tr && !bl && !br) continue;
            if (g_ngrp >= MAX_GROUPS) return;
            Group* g = &g_groups[g_ngrp++];
            g->frame = frame; g->line = li; g->pos = n;
            g->tiles[0]=tl; g->tiles[1]=tr; g->tiles[2]=bl; g->tiles[3]=br;
            uint8_t buf[128];
            uint16_t idxs[4] = {tl, tr, bl, br};
            for (int cb = 0; cb < 4; cb++) {
                for (int t = 0; t < 4; t++) {
                    size_t off = (size_t)cb * CHARBLOCK_SIZE + (size_t)idxs[t] * TILE_BYTES;
                    if (off + TILE_BYTES > VRAM_BG_BYTES) {
                        memset(buf + t*TILE_BYTES, 0, TILE_BYTES);
                    } else {
                        memcpy(buf + t*TILE_BYTES, vram + off, TILE_BYTES);
                    }
                }
                fp16(buf, g->fps[cb]);
            }
        }
    }
}

static void quiet_log(struct mLogger* l, int category, enum mLogLevel level,
                      const char* fmt, va_list args) {
    (void)l; (void)category; (void)level; (void)fmt; (void)args;
}
static struct mLogger g_log_quiet = { .log = quiet_log };

enum { KEY_A=1, KEY_B=2, KEY_SELECT=4, KEY_START=8, KEY_RIGHT=16, KEY_LEFT=32,
       KEY_UP=64, KEY_DOWN=128, KEY_R=256, KEY_L=512 };
static uint32_t parse_keys(const char* s) {
    if (!s || !*s) return 0;
    uint32_t k = 0;
    char tmp[256]; strncpy(tmp, s, sizeof tmp - 1); tmp[sizeof tmp - 1] = 0;
    for (char* tok = strtok(tmp, ","); tok; tok = strtok(NULL, ",")) {
        if (!strcasecmp(tok, "A")) k |= KEY_A;
        else if (!strcasecmp(tok, "B")) k |= KEY_B;
        else if (!strcasecmp(tok, "SELECT")) k |= KEY_SELECT;
        else if (!strcasecmp(tok, "START")) k |= KEY_START;
        else if (!strcasecmp(tok, "RIGHT")) k |= KEY_RIGHT;
        else if (!strcasecmp(tok, "LEFT"))  k |= KEY_LEFT;
        else if (!strcasecmp(tok, "UP"))    k |= KEY_UP;
        else if (!strcasecmp(tok, "DOWN"))  k |= KEY_DOWN;
    }
    return k;
}

static void write_json(const char* path, const char* rom, uint64_t frames_run, uint32_t bp_pc) {
    FILE* f = fopen(path, "w");
    if (!f) { fprintf(stderr, "cannot open %s\n", path); return; }
    fprintf(f, "{\n  \"rom\": \"%s\",\n  \"breakpoint_pc\": %u,\n"
              "  \"frames_run\": %llu,\n  \"break_hits\": %d,\n",
            rom, bp_pc, (unsigned long long)frames_run, g_hits);
    fprintf(f, "  \"tokens\": [\n");
    for (size_t i = 0; i < g_ntok; i++) {
        Token* t = &g_tokens[i];
        fprintf(f, "    {\"frame\":%llu,\"pc\":%u,\"page\":%u,\"idx\":%u,\"r0\":%u}%s\n",
                (unsigned long long)t->frame, t->pc, t->page, t->idx, t->r0,
                i + 1 == g_ntok ? "" : ",");
    }
    fprintf(f, "  ],\n  \"groups\": [\n");
    for (size_t i = 0; i < g_ngrp; i++) {
        Group* g = &g_groups[i];
        fprintf(f, "    {\"frame\":%llu,\"line\":%d,\"pos\":%d,"
                   "\"tiles\":[%u,%u,%u,%u],\"fps\":[\"%s\",\"%s\",\"%s\",\"%s\"]}%s\n",
                (unsigned long long)g->frame, g->line, g->pos,
                g->tiles[0], g->tiles[1], g->tiles[2], g->tiles[3],
                g->fps[0], g->fps[1], g->fps[2], g->fps[3],
                i + 1 == g_ngrp ? "" : ",");
    }
    fprintf(f, "  ]\n}\n");
    fclose(f);
}

int main(int argc, char** argv) {
    const char* romPath = NULL;
    const char* outPath = ".moneo-artifacts/capture.json";
    uint64_t maxFrames = 60ull * 60ull * 5ull;
    int snapshotEvery = 30;
    uint32_t bpPC = 0x080062B4;
    bool quiet = true;
    uint32_t pressKeys = KEY_A;

    static struct option opts[] = {
        {"rom",        required_argument, 0, 'r'},
        {"out",        required_argument, 0, 'o'},
        {"frames",     required_argument, 0, 'f'},
        {"seconds",    required_argument, 0, 's'},
        {"press",      required_argument, 0, 'p'},
        {"snapshot-frames", required_argument, 0, 'n'},
        {"break-pc",   required_argument, 0, 'b'},
        {"verbose",    no_argument,       0, 'v'},
        {0,0,0,0}
    };
    int c, oi = 0;
    while ((c = getopt_long(argc, argv, "r:o:f:s:p:n:b:v", opts, &oi)) != -1) {
        switch (c) {
            case 'r': romPath = optarg; break;
            case 'o': outPath = optarg; break;
            case 'f': maxFrames = strtoull(optarg, NULL, 0); break;
            case 's': maxFrames = strtoull(optarg, NULL, 0) * 60; break;
            case 'p': pressKeys = parse_keys(optarg); break;
            case 'n': snapshotEvery = atoi(optarg); break;
            case 'b': bpPC = (uint32_t)strtoul(optarg, NULL, 0); break;
            case 'v': quiet = false; break;
            default:  return 2;
        }
    }
    if (!romPath) {
        fprintf(stderr, "usage: %s --rom <rom.gba> [--out <out.json>] [--frames N|--seconds S]\n", argv[0]);
        return 2;
    }

    fprintf(stderr, "[capture] start; rom=%s\n", romPath);
    /* if (quiet) mLogSetDefaultLogger(&g_log_quiet); */
    (void)quiet;
    signal(SIGINT, on_sigint);

    g_core = GBACoreCreate();
    fprintf(stderr, "[capture] core created\n");
    if (!g_core) { fprintf(stderr, "GBACoreCreate failed\n"); return 1; }
    g_core->init(g_core);
    fprintf(stderr, "[capture] core init\n");
    mCoreInitConfig(g_core, "mgba_capture");
    fprintf(stderr, "[capture] core config\n");

    struct VFile* vf = VFileOpen(romPath, O_RDONLY);
    if (!vf || !g_core->loadROM(g_core, vf)) {
        fprintf(stderr, "loadROM failed: %s\n", romPath); return 1;
    }
    g_core->reset(g_core);
    fprintf(stderr, "[capture] core reset\n");

    memset(&g_debugger, 0, sizeof g_debugger);
    mDebuggerInit(&g_debugger);
    fprintf(stderr, "[capture] dbg init\n");
    mDebuggerAttach(&g_debugger, g_core);

    memset(&g_module, 0, sizeof g_module);
    g_module.type      = DEBUGGER_CUSTOM;
    g_module.init      = mod_init;
    g_module.deinit    = mod_deinit;
    g_module.paused    = mod_paused;
    g_module.update    = mod_update;
    g_module.entered   = mod_entered;
    g_module.custom    = mod_custom;
    g_module.interrupt = mod_interrupt;
    mDebuggerAttachModule(&g_debugger, &g_module);

    g_debugger.state = DEBUGGER_RUNNING;
    fprintf(stderr, "[capture] debugger attached, module type=%d\n", g_module.type);

    struct mBreakpoint bp = {
        .address     = bpPC,
        .segment     = -1,
        .type        = BREAKPOINT_SOFTWARE,
        .condition   = NULL,
        .disabled    = false,
        .isTemporary = false,
    };
    ssize_t bpId = g_debugger.platform->setBreakpoint(g_debugger.platform, &g_module, &bp);
    fprintf(stderr, "[capture] setBreakpoint @ 0x%08x → id=%zd\n", bpPC, bpId);

    fprintf(stderr, "[capture] running for up to %llu frames; presskeys=0x%x; snapshot every %d\n",
            (unsigned long long)maxFrames, pressKeys, snapshotEvery);

    uint64_t frame = 0;
    uint32_t holdPattern[] = { pressKeys, pressKeys, 0, 0 };
    while (!g_stop && frame < maxFrames) {
        g_core->setKeys(g_core, holdPattern[(frame >> 3) & 3]);
        mDebuggerRunFrame(&g_debugger);
        frame++;
        if ((int)(frame % snapshotEvery) == 0) {
            capture_groups(frame);
            if (frame % (uint64_t)(snapshotEvery * 60) == 0) {
                fprintf(stderr, "[capture] frame=%llu  tokens=%zu  groups=%zu  hits=%d\n",
                        (unsigned long long)frame, g_ntok, g_ngrp, g_hits);
            }
        }
    }

    fprintf(stderr, "[capture] done. frames=%llu tokens=%zu groups=%zu hits=%d\n",
            (unsigned long long)frame, g_ntok, g_ngrp, g_hits);

    write_json(outPath, romPath, frame, bpPC);
    fprintf(stderr, "[capture] wrote %s\n", outPath);

    g_core->deinit(g_core);
    return 0;
}

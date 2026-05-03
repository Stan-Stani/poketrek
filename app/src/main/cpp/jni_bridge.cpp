// JNI bridge between Kotlin and the embedded mGBA core.
//
// Phase 0 surface: loadRom, runFrame, getFramebuffer, getFramebufferHash, destroy.
// Phase 1 will add: setKeyState, audio pull, save state.
// Phase 3a will add: busRead8/16/32 + frame callback hook.

#include <jni.h>
#include <android/log.h>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <mutex>
#include <vector>

extern "C" {
#include <mgba/core/core.h>
#include <mgba/core/blip_buf.h>
#include <mgba/core/config.h>
#include <mgba/gba/core.h>
#include <mgba-util/vfs.h>
}

#include "movement_gate.h"

#define LOG_TAG "poketrek-jni"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

namespace {

constexpr int GBA_WIDTH = 240;
constexpr int GBA_HEIGHT = 160;
constexpr int FRAMEBUFFER_BYTES = GBA_WIDTH * GBA_HEIGHT * 4;

struct Emulator {
    mCore* core = nullptr;
    std::vector<uint8_t> framebuffer;  // RGBA8888, GBA_WIDTH * GBA_HEIGHT * 4
    std::vector<uint8_t> romCopy;      // mGBA expects ROM memory to outlive loadROM
    std::mutex mutex;
    MovementGate gate;

    Emulator() : framebuffer(FRAMEBUFFER_BYTES, 0) {}

    ~Emulator() {
        if (core) {
            core->deinit(core);
            core = nullptr;
        }
    }
};

std::unique_ptr<Emulator> g_emulator;

uint64_t fnv1a64(const uint8_t* data, size_t len) {
    uint64_t hash = 0xcbf29ce484222325ULL;
    for (size_t i = 0; i < len; ++i) {
        hash ^= data[i];
        hash *= 0x100000001b3ULL;
    }
    return hash;
}

}  // namespace

extern "C" JNIEXPORT jboolean JNICALL
Java_com_poketrek_emu_NativeEmulator_loadRom(JNIEnv* env, jobject /*thiz*/, jbyteArray romBytes) {
    if (g_emulator) {
        LOGI("loadRom called while emulator alive — recreating");
        g_emulator.reset();
    }

    auto emu = std::make_unique<Emulator>();
    emu->core = GBACoreCreate();
    if (!emu->core) {
        LOGE("GBACoreCreate failed");
        return JNI_FALSE;
    }
    // mCoreInitConfig sets up internal hash tables and config state. Must run
    // before core->init() — without it, GBALoadROM crashes inside the game-DB
    // lookup with an uninitialized table.
    mCoreInitConfig(emu->core, nullptr);
    if (!emu->core->init(emu->core)) {
        LOGE("core->init failed");
        return JNI_FALSE;
    }

    emu->core->setVideoBuffer(emu->core,
                              reinterpret_cast<color_t*>(emu->framebuffer.data()),
                              GBA_WIDTH);

    // Copy the ROM bytes into a buffer we own. The libretro reference does this
    // (line 857–860 of platform/libretro/libretro.c) because mGBA may keep the
    // pointer alive past loadROM and the JNI array's lifetime is unreliable.
    jsize len = env->GetArrayLength(romBytes);
    emu->romCopy.resize(static_cast<size_t>(len));
    env->GetByteArrayRegion(romBytes, 0, len,
                            reinterpret_cast<jbyte*>(emu->romCopy.data()));
    VFile* vf = VFileFromMemory(emu->romCopy.data(), emu->romCopy.size());
    if (!vf) {
        LOGE("VFileFromMemory failed");
        return JNI_FALSE;
    }
    if (!emu->core->loadROM(emu->core, vf)) {
        LOGE("loadROM failed");
        return JNI_FALSE;
    }
    emu->core->reset(emu->core);

    g_emulator = std::move(emu);
    LOGI("ROM loaded; emulator ready");
    return JNI_TRUE;
}

extern "C" JNIEXPORT void JNICALL
Java_com_poketrek_emu_NativeEmulator_runFrame(JNIEnv* /*env*/, jobject /*thiz*/) {
    if (!g_emulator || !g_emulator->core) return;
    std::lock_guard<std::mutex> lock(g_emulator->mutex);
    g_emulator->core->runFrame(g_emulator->core);
}

extern "C" JNIEXPORT jbyteArray JNICALL
Java_com_poketrek_emu_NativeEmulator_getFramebuffer(JNIEnv* env, jobject /*thiz*/) {
    if (!g_emulator) return nullptr;
    std::lock_guard<std::mutex> lock(g_emulator->mutex);
    jbyteArray out = env->NewByteArray(FRAMEBUFFER_BYTES);
    env->SetByteArrayRegion(out, 0, FRAMEBUFFER_BYTES,
                            reinterpret_cast<const jbyte*>(g_emulator->framebuffer.data()));
    return out;
}

extern "C" JNIEXPORT jlong JNICALL
Java_com_poketrek_emu_NativeEmulator_getFramebufferHash(JNIEnv* /*env*/, jobject /*thiz*/) {
    if (!g_emulator) return 0;
    std::lock_guard<std::mutex> lock(g_emulator->mutex);
    return static_cast<jlong>(fnv1a64(g_emulator->framebuffer.data(), FRAMEBUFFER_BYTES));
}

extern "C" JNIEXPORT void JNICALL
Java_com_poketrek_emu_NativeEmulator_destroy(JNIEnv* /*env*/, jobject /*thiz*/) {
    g_emulator.reset();
}

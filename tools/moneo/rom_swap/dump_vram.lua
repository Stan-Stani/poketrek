-- mGBA Lua: advance through GameFreak intro by holding START, then dump
-- VRAM/EWRAM/palette once we reach the title screen.
-- Usage: mgba --script dump_vram.lua leafgreen_J-K_2024.gba

local FRAMES_HOLD_START = 480   -- ~8s at 60fps; long enough to skip intro
local FRAMES_BEFORE_DUMP = 720  -- ~12s; should be on title screen by then
local OUT_DIR = "/tmp"
local frame = 0
local done = false

-- mGBA key bits: A=1 B=2 SELECT=4 START=8 RIGHT=10 LEFT=20 UP=40 DOWN=80 R=100 L=200
local KEY_START = 8
local KEY_A = 1

local function dump_range(label, addr, length)
    local f = io.open(OUT_DIR .. "/" .. label, "wb")
    if not f then console:error("could not open " .. label); return end
    local CHUNK = 0x1000
    local off = 0
    while off < length do
        local n = math.min(CHUNK, length - off)
        f:write(emu:readRange(addr + off, n))
        off = off + n
    end
    f:close()
    console:log(string.format("dumped %s: %#x bytes from %#x", label, length, addr))
end

local function on_frame()
    frame = frame + 1
    -- Hold START then A in alternation across the boot phase to advance
    -- through the GameFreak/Nintendo logos and pause on the title screen
    -- press-start prompt.
    if frame >= 60 and frame <= FRAMES_HOLD_START then
        if (frame % 60) < 30 then
            emu:addKey(KEY_START)
        else
            emu:clearKey(KEY_START)
            emu:addKey(KEY_A)
        end
    elseif frame == FRAMES_HOLD_START + 1 then
        emu:clearKey(KEY_START)
        emu:clearKey(KEY_A)
    end

    if frame == FRAMES_BEFORE_DUMP and not done then
        done = true
        console:log(string.format("Frame %d — dumping memory", frame))
        dump_range("vram_at_title.bin",   0x06000000, 0x18000)
        dump_range("palette_at_title.bin", 0x05000000, 0x400)
        dump_range("oam_at_title.bin",     0x07000000, 0x400)
        dump_range("ewram_at_title.bin",   0x02000000, 0x40000)
        dump_range("iwram_at_title.bin",   0x03000000, 0x08000)
        console:log("DONE")
    end
end

callbacks:add("frame", on_frame)
console:log("dump_vram.lua loaded — advance + dump at frame " .. FRAMES_BEFORE_DUMP)

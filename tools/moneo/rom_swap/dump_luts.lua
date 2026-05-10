-- Drive into Oak's dialog, then dump the runtime LUT state needed by the
-- glyph decoder at 0x08002fa0:
--   - ROM LUT at 0x081ea090, 256 bytes (also can be read from the ROM
--     file directly, but dumped for verification)
--   - IWRAM LUT at 0x03000a40, 512 bytes (the halfword table; populated
--     at boot, so it's only valid after the engine has initialized)
--   - IWRAM staging buffer at 0x03003da0..0x03003e30 once Oak's dialog
--     is rendering (so we have a reference glyph layout to reverse the
--     decoder against)

local OUT_DIR = "/tmp/poketrek_trace"
os.execute("mkdir -p " .. OUT_DIR)

local A     = 1
local START = 8

local DUMP_FRAME = 700

local frame = 0
local last_keys = 0
local done = false

local function input_for_frame(f)
    local phase = math.floor(f / 8) % 2
    if f < 240 then return 0 end
    if f < 720 then
        if phase == 0 then return A else return START end
    end
    if f < 900 then return 0 end
    if f < 2400 then
        if phase == 0 then return A else return 0 end
    end
    return 0
end

local function dump(label, addr, len)
    local f = io.open(OUT_DIR .. "/" .. label, "wb")
    f:write(emu:readRange(addr, len))
    f:close()
end

local function on_frame()
    if done then return end
    frame = frame + 1
    local desired = input_for_frame(frame)
    if desired ~= last_keys then
        emu:clearKeys(0xFFFF)
        if desired ~= 0 then emu:addKeys(desired) end
        last_keys = desired
    end
    if frame == DUMP_FRAME then
        if emu.screenshot then
            emu:screenshot(OUT_DIR .. "/lut_dump_screen.png")
        end
        dump("rom_lut_081ea090.bin",   0x081ea090, 256)
        dump("iwram_lut_03000a40.bin", 0x03000a40, 512)
        dump("iwram_stage_03003da0.bin", 0x03003da0, 0x100)
        dump("ewram_cache_02007800.bin", 0x02007800, 0x1800)
        console:log("dumped LUTs at frame " .. frame)
        done = true
    end
end

callbacks:add("frame", on_frame)
console:log("dump_luts.lua loaded")

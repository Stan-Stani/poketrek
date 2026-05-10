-- Drive the 2024 Korean LeafGreen past the GameFreak intro, title, menu,
-- and into Professor Oak's intro dialog. Dump VRAM/EWRAM + a PNG screenshot
-- every N frames so we can pick the one where the dialog font is on screen.

local OUT_DIR = "/tmp/poketrek_drive"
os.execute("mkdir -p " .. OUT_DIR)

-- mGBA key bits
local A      = 1
local B      = 2
local SELECT = 4
local START  = 8
local RIGHT  = 0x10
local LEFT   = 0x20
local UP     = 0x40
local DOWN   = 0x80

local frame = 0
local snapshot_idx = 0
-- Dump cadence: snapshot every 30 frames once we're past the intro.
local SNAPSHOT_EVERY = 30
local FIRST_SNAPSHOT = 360
local LAST_SNAPSHOT  = 1800   -- ~30s of in-game time

local function dump_range(label, addr, length)
    local f = io.open(OUT_DIR .. "/" .. label, "wb")
    if not f then console:error("open failed: " .. label); return end
    local CHUNK = 0x1000
    local off = 0
    while off < length do
        local n = math.min(CHUNK, length - off)
        f:write(emu:readRange(addr + off, n))
        off = off + n
    end
    f:close()
end

local function snapshot(idx)
    local prefix = string.format("%s/%03d_f%05d", OUT_DIR, idx, frame)
    dump_range(string.format("%03d_f%05d_vram.bin",  idx, frame), 0x06000000, 0x18000)
    dump_range(string.format("%03d_f%05d_ewram.bin", idx, frame), 0x02000000, 0x40000)
    dump_range(string.format("%03d_f%05d_pal.bin",   idx, frame), 0x05000000, 0x400)
    -- Screenshot
    if emu.screenshot then
        emu:screenshot(prefix .. ".png")
    end
    console:log(string.format("snapshot %d at frame %d", idx, frame))
end

-- Input plan (frame ranges, function returning a key bit-mask).
-- - 0..240   : nothing (let GameFreak fade-in start)
-- - 240..540 : tap A (skip GameFreak + Nintendo logos, dismiss title)
-- - 540..720 : nothing (let menu render)
-- - 720..900 : tap A on "New Game" (top option in continue menu)
-- - 900..1100: tap A repeatedly (advance through Oak's first speech bubbles)
-- - 1100+   : keep tapping A
local function input_for_frame(f)
    -- alternating press/release every 8 frames (≈7 Hz) of whichever key applies
    local phase = math.floor(f / 8) % 2
    if f < 240 then
        return 0
    elseif f < 720 then
        -- tap A and START in alternation to cover both "any key" prompts and "PRESS START"
        if phase == 0 then return A else return START end
    elseif f < 900 then
        return 0  -- pause for menu to render
    elseif f < 2400 then
        if phase == 0 then return A else return 0 end  -- tap A repeatedly
    end
    return 0
end

local last_keys = 0
local function on_frame()
    frame = frame + 1
    -- Apply input
    local desired = input_for_frame(frame)
    if desired ~= last_keys then
        emu:clearKeys(0xFFFF)
        if desired ~= 0 then emu:addKeys(desired) end
        last_keys = desired
    end
    -- Snapshots
    if frame >= FIRST_SNAPSHOT and frame <= LAST_SNAPSHOT and (frame % SNAPSHOT_EVERY) == 0 then
        snapshot_idx = snapshot_idx + 1
        snapshot(snapshot_idx)
    end
    if frame == LAST_SNAPSHOT + 1 then
        console:log("DONE — captured " .. snapshot_idx .. " snapshots")
    end
end

callbacks:add("frame", on_frame)
console:log("drive_to_dialog.lua loaded — output → " .. OUT_DIR)

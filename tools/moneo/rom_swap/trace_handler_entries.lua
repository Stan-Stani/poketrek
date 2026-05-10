-- Capture every entry into one of the 6 jamo handlers identified earlier:
-- 0x800645c, 0x8006504, 0x80065cc, 0x8006738, 0x8006800, 0x800696c.
-- At each entry record the codepoint passed in (r0) plus r1..r3, lr, sp.
-- This tells us how the dispatcher transforms the BE16 storage codepoint
-- (0x3700..0x40FF) into the value used by `font_base + cp * 64`.
--
-- Strategy: drive into Oak's dialog, then single-step ~3M instructions
-- and check PC against the handler-entry set on every step. Mass writes
-- to JSONL on each match.

local OUT_DIR = "/tmp/poketrek_trace"
os.execute("mkdir -p " .. OUT_DIR)

local A     = 1
local START = 8

local DETECT_FROM = 240
local DETECT_UNTIL = 1500
local TRACE_STEPS = 3 * 1024 * 1024

-- handler entry addresses (Thumb mode -> low bit 0)
local HANDLERS = {
    [0x0800645c] = "h0",
    [0x08006504] = "h1",
    [0x080065cc] = "h2",
    [0x08006738] = "h3",
    [0x08006800] = "h4",
    [0x0800696c] = "h5",
}
-- also catch the dispatcher entry to see codepoint at top of pipeline
HANDLERS[0x080057a4] = "disp"

-- Hash lookup
local function is_handler_entry(pc)
    return HANDLERS[pc]
end

local frame = 0
local last_keys = 0
local prev_full = nil
local trace_done = false

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

local CACHE_BASE = 0x02007800
local CACHE_END  = 0x02009000
local CACHE_LEN  = CACHE_END - CACHE_BASE

local function snapshot_cache()
    return emu:readRange(CACHE_BASE, CACHE_LEN)
end

local trace_jsonl
local events = 0
local MAX_EVENTS = 4096

local function dump(label, pc, step)
    local r = {}
    for i = 0, 12 do r[i] = emu:readRegister("r" .. i) end
    local lr = emu:readRegister("lr")
    local sp = emu:readRegister("sp")
    trace_jsonl:write(string.format(
        "{\"step\":%d,\"label\":\"%s\",\"pc\":%d,\"lr\":%d,\"sp\":%d," ..
        "\"r0\":%d,\"r1\":%d,\"r2\":%d,\"r3\":%d," ..
        "\"r4\":%d,\"r5\":%d,\"r6\":%d,\"r7\":%d," ..
        "\"r8\":%d,\"r9\":%d,\"r10\":%d,\"r11\":%d,\"r12\":%d}\n",
        step, label, pc, lr, sp,
        r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7],
        r[8], r[9], r[10], r[11], r[12]))
    trace_jsonl:flush()
    events = events + 1
end

local function run_trace()
    console:log("trace: entering single-step")
    if emu.screenshot then emu:screenshot(OUT_DIR .. "/handler_pre.png") end
    trace_jsonl = io.open(OUT_DIR .. "/handler_trace.jsonl", "w")
    local step = 0
    while step < TRACE_STEPS and events < MAX_EVENTS do
        emu:step()
        step = step + 1
        local pc = emu:readRegister("pc")
        local label = is_handler_entry(pc)
        if label then
            dump(label, pc, step)
        end
        if (step % 65536) == 0 then
            console:log(string.format("trace: step=%d events=%d", step, events))
        end
    end
    if emu.screenshot then emu:screenshot(OUT_DIR .. "/handler_post.png") end
    console:log(string.format("trace: DONE steps=%d events=%d", step, events))
    trace_jsonl:close()
    trace_done = true
end

local function on_frame()
    if trace_done then return end
    frame = frame + 1
    local desired = input_for_frame(frame)
    if desired ~= last_keys then
        emu:clearKeys(0xFFFF)
        if desired ~= 0 then emu:addKeys(desired) end
        last_keys = desired
    end
    if frame < DETECT_FROM or frame > DETECT_UNTIL then return end
    local cur = snapshot_cache()
    if prev_full and cur ~= prev_full then
        console:log(string.format("trace: cache delta at frame=%d", frame))
        run_trace()
        return
    end
    prev_full = cur
end

callbacks:add("frame", on_frame)
console:log("trace_handler_entries.lua loaded")

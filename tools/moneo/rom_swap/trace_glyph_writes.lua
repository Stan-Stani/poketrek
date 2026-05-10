-- Hunt for the Korean glyph composer in 2024-patched LeafGreen by detecting
-- writes to the EWRAM glyph cache (0x02007800..0x02009000) and capturing
-- the executing CPU state at the moment of each write.
--
-- Approach (no native write-trap exists in mGBA's Lua API):
--   1. Drive the game normally past intro into Oak's dialog.
--   2. Each frame, hash the glyph cache. The first frame whose hash
--      differs from the prior frame is when the typewriter ticked.
--   3. Switch into single-step mode: call emu:step() in a tight loop for
--      ~5M instructions (~17 emulated frames -- enough to catch several
--      more typewriter ticks). Every SAMPLE_EVERY steps, snapshot the
--      cache via emu:readRange (fast: one C-side loop). On any diff,
--      record PC + r0..r12 + the byte deltas.
--
-- Output: /tmp/poketrek_trace/{trace.log, trace.jsonl, pre_trace.png,
--                              compose_frame.png, post_compose.png}

local OUT_DIR = "/tmp/poketrek_trace"
os.execute("mkdir -p " .. OUT_DIR)

local CACHE_BASE = 0x02007800
local CACHE_END  = 0x02009000   -- exclusive
local CACHE_LEN  = CACHE_END - CACHE_BASE

local A     = 1
local START = 8

local DETECT_FROM   = 240
local DETECT_UNTIL  = 1500
local SAMPLE_EVERY  = 4
local MAX_STEPS     = 5 * 1024 * 1024
local MAX_EVENTS    = 1024

local frame = 0
local last_keys = 0
local prev_full = nil
local trace_done = false

local function input_for_frame(f)
    local phase = math.floor(f / 8) % 2
    if f < 240 then
        return 0
    elseif f < 720 then
        if phase == 0 then return A else return START end
    elseif f < 900 then
        return 0
    elseif f < 2400 then
        if phase == 0 then return A else return 0 end
    end
    return 0
end

local function snapshot_cache()
    return emu:readRange(CACHE_BASE, CACHE_LEN)
end

local function diff_cache(prev, cur)
    -- Returns up to 64 deltas: { offset, prev_byte, cur_byte }.
    local diffs = {}
    if not prev then return diffs end
    local n = #cur
    for i = 1, n do
        local a = string.byte(prev, i)
        local b = string.byte(cur, i)
        if a ~= b then
            table.insert(diffs, { i - 1, a, b })
            if #diffs >= 64 then return diffs end
        end
    end
    return diffs
end

local trace_log
local trace_jsonl
local events = 0

local function dump_event(step_count, prev_cache, cur_cache)
    local diffs = diff_cache(prev_cache, cur_cache)
    if #diffs == 0 then return end
    local pc   = emu:readRegister("pc")
    local lr   = emu:readRegister("lr")
    local sp   = emu:readRegister("sp")
    local cpsr = emu:readRegister("cpsr")
    local r = {}
    for i = 0, 12 do r[i] = emu:readRegister("r" .. i) end

    trace_log:write(string.format(
        "step=%d pc=%08x lr=%08x cpsr=%08x\n" ..
        "  r0=%08x r1=%08x r2=%08x r3=%08x\n" ..
        "  r4=%08x r5=%08x r6=%08x r7=%08x\n" ..
        "  r8=%08x r9=%08x r10=%08x r11=%08x r12=%08x sp=%08x\n",
        step_count, pc, lr, cpsr,
        r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7],
        r[8], r[9], r[10], r[11], r[12], sp))
    for _, d in ipairs(diffs) do
        trace_log:write(string.format(
            "  cache[%08x] %02x -> %02x\n",
            CACHE_BASE + d[1], d[2], d[3]))
    end
    trace_log:write("\n")

    local diff_parts = {}
    for _, d in ipairs(diffs) do
        table.insert(diff_parts, string.format(
            "{\"addr\":%d,\"prev\":%d,\"cur\":%d}",
            CACHE_BASE + d[1], d[2], d[3]))
    end
    trace_jsonl:write(string.format(
        "{\"step\":%d,\"pc\":%d,\"lr\":%d,\"cpsr\":%d," ..
        "\"r0\":%d,\"r1\":%d,\"r2\":%d,\"r3\":%d," ..
        "\"r4\":%d,\"r5\":%d,\"r6\":%d,\"r7\":%d," ..
        "\"r8\":%d,\"r9\":%d,\"r10\":%d,\"r11\":%d,\"r12\":%d,\"sp\":%d," ..
        "\"diffs\":[%s]}\n",
        step_count, pc, lr, cpsr,
        r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7],
        r[8], r[9], r[10], r[11], r[12], sp,
        table.concat(diff_parts, ",")))
    trace_log:flush()
    trace_jsonl:flush()
    events = events + 1
end

local function run_single_step_trace()
    console:log("trace: entering single-step mode")
    if emu.screenshot then
        emu:screenshot(OUT_DIR .. "/compose_frame.png")
    end
    trace_log = io.open(OUT_DIR .. "/trace.log", "w")
    trace_jsonl = io.open(OUT_DIR .. "/trace.jsonl", "w")

    local prev_snap = snapshot_cache()
    local step = 0
    while step < MAX_STEPS and events < MAX_EVENTS do
        emu:step()
        step = step + 1
        if (step % SAMPLE_EVERY) == 0 then
            local cur_snap = snapshot_cache()
            if cur_snap ~= prev_snap then
                dump_event(step, prev_snap, cur_snap)
                prev_snap = cur_snap
            end
        end
        if (step % 65536) == 0 then
            console:log(string.format(
                "trace: step=%d events=%d", step, events))
        end
    end

    if emu.screenshot then
        emu:screenshot(OUT_DIR .. "/post_compose.png")
    end
    console:log(string.format(
        "trace: DONE (steps=%d events=%d)", step, events))
    trace_log:close()
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

    if frame < DETECT_FROM or frame > DETECT_UNTIL then
        return
    end

    local cur = snapshot_cache()
    if prev_full and cur ~= prev_full then
        console:log(string.format(
            "trace: cache changed at frame=%d", frame))
        if emu.screenshot then
            emu:screenshot(OUT_DIR .. "/pre_trace.png")
        end
        run_single_step_trace()
        return
    end
    prev_full = cur
end

callbacks:add("frame", on_frame)
console:log("trace_glyph_writes.lua loaded -- output -> " .. OUT_DIR)

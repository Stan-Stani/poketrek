#pragma once

#include <atomic>
#include <cstdint>

// Phase 3b will fill this in. For Phase 0 we declare the type so jni_bridge.cpp
// can hold an instance without pulling in the (yet-unwritten) gate logic.
struct MovementGate {
    std::atomic<int32_t> budget{0};
    std::atomic<uint16_t> rawKeyBitmask{0};

    // Returns the bitmask the core should see, after applying the gate.
    uint16_t filter(uint16_t raw, bool inOverworld) const;
};

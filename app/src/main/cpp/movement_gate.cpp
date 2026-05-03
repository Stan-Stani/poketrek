#include "movement_gate.h"

// GBA KEYINPUT bits (active-high in mGBA's `setKeys` representation).
// 0=A, 1=B, 2=Sel, 3=Start, 4=Right, 5=Left, 6=Up, 7=Down, 8=R, 9=L
static constexpr uint16_t kRight = 1 << 4;
static constexpr uint16_t kLeft  = 1 << 5;
static constexpr uint16_t kUp    = 1 << 6;
static constexpr uint16_t kDown  = 1 << 7;
static constexpr uint16_t kDirMask = kRight | kLeft | kUp | kDown;

uint16_t MovementGate::filter(uint16_t raw, bool inOverworld) const {
    if (!inOverworld) return raw;
    if (budget.load(std::memory_order_relaxed) > 0) return raw;
    return raw & ~kDirMask;
}

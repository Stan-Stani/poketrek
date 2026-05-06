package com.poketrek.emu

/**
 * Writes Rare Candies into the FRLG bag's items pocket via emulator RAM bus.
 *
 * Layout (verified against pokefirered include/global.h):
 *   - SaveBlock1 pointer at 0x03005008 → +0x310 = bagPocket_Items[42]
 *   - SaveBlock2 pointer at 0x0300500C → +0xF20 = encryptionKey (u32)
 *   - struct ItemSlot { u16 itemId; u16 quantity; }   // 4 bytes per slot
 *   - quantity is XORed with the low 16 bits of encryptionKey
 *   - FRLG keeps a single stack per item ID, max 999
 *   - ITEM_RARE_CANDY = 68 (0x44), same in all Gen 3
 *
 * Gated to LEAFGREEN_US_REV1 by callers — addresses are not valid on the
 * Korean build until runtime calibration lands.
 */
object RareCandyShop {
    const val ITEM_RARE_CANDY: Int = 68
    const val ITEM_NONE: Int = 0
    const val MAX_STACK: Int = 999
    const val BAG_ITEMS_COUNT: Int = 42

    private const val SAVE_BLOCK1_PTR = 0x03005008
    private const val SAVE_BLOCK2_PTR = 0x0300500C
    private const val BAG_ITEMS_OFFSET = 0x310
    private const val ENCRYPTION_KEY_OFFSET = 0xF20

    /** Tiny surface so we can unit-test on the JVM without the native core. */
    interface BusIO {
        fun read16(addr: Int): Int
        fun read32(addr: Int): Int
        fun write16(addr: Int, value: Int)
    }

    sealed class Result {
        object Ok : Result()
        /** SaveBlock pointers point outside EWRAM/IWRAM — title screen, etc. */
        object NotInGame : Result()
        /** No empty slot to start a new stack and no existing stack with room. */
        object BagFull : Result()
        /** Existing stack would exceed 999 with the requested count. */
        data class StackOverflow(val existing: Int, val requested: Int) : Result()
    }

    fun addRareCandy(io: BusIO, count: Int): Result {
        require(count in 1..MAX_STACK) { "count out of range: $count" }
        val sb1 = io.read32(SAVE_BLOCK1_PTR)
        val sb2 = io.read32(SAVE_BLOCK2_PTR)
        if (!ptrInWram(sb1) || !ptrInWram(sb2)) return Result.NotInGame

        val key16 = io.read16(sb2 + ENCRYPTION_KEY_OFFSET)

        val slotsBase = sb1 + BAG_ITEMS_OFFSET
        var firstEmpty = -1
        for (i in 0 until BAG_ITEMS_COUNT) {
            val slotAddr = slotsBase + i * 4
            val itemId = io.read16(slotAddr)
            if (itemId == ITEM_RARE_CANDY) {
                val encQty = io.read16(slotAddr + 2)
                val realQty = encQty xor key16
                if (realQty + count > MAX_STACK) {
                    return Result.StackOverflow(realQty, count)
                }
                writeQuantity(io, slotAddr + 2, realQty + count, key16)
                return Result.Ok
            }
            if (itemId == ITEM_NONE && firstEmpty < 0) firstEmpty = i
        }
        if (firstEmpty < 0) return Result.BagFull
        val emptyAddr = slotsBase + firstEmpty * 4
        io.write16(emptyAddr, ITEM_RARE_CANDY)
        writeQuantity(io, emptyAddr + 2, count, key16)
        return Result.Ok
    }

    private fun writeQuantity(io: BusIO, addr: Int, realQty: Int, key16: Int) {
        io.write16(addr, (realQty xor key16) and 0xFFFF)
    }

    // Pointers into EWRAM (0x02xxxxxx) or IWRAM (0x03xxxxxx). Anything else
    // means the SaveBlock isn't initialized yet (title screen / intro) and
    // we'd be writing to garbage.
    private fun ptrInWram(p: Int): Boolean {
        if (p == 0) return false
        val region = p ushr 24
        return region == 0x02 || region == 0x03
    }
}

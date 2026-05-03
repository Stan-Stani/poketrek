package com.poketrek.emu

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Fakes the GBA bus with two flat 2 KiB regions of EWRAM-like memory: one
 * for SaveBlock1, one for SaveBlock2. Mounts them at fixed pointers and
 * publishes those pointers at 0x03005008 / 0x0300500C the way the FRLG
 * runtime does, so RareCandyShop can drive the same memory layout it would
 * see in-game.
 */
private class FakeBus : RareCandyShop.BusIO {
    private val memory = HashMap<Int, Int>() // byte-addressed
    val sb1Base = 0x02020000
    val sb2Base = 0x02030000

    init {
        // Pointer cells the shop derefs.
        write32(0x03005008, sb1Base)
        write32(0x0300500C, sb2Base)
    }

    fun write32(addr: Int, value: Int) {
        memory[addr]     = value         and 0xFF
        memory[addr + 1] = (value ushr 8)  and 0xFF
        memory[addr + 2] = (value ushr 16) and 0xFF
        memory[addr + 3] = (value ushr 24) and 0xFF
    }

    override fun read32(addr: Int): Int {
        return  (memory[addr]     ?: 0)        or
               ((memory[addr + 1] ?: 0) shl 8) or
               ((memory[addr + 2] ?: 0) shl 16) or
               ((memory[addr + 3] ?: 0) shl 24)
    }
    override fun read16(addr: Int): Int =
        (memory[addr] ?: 0) or ((memory[addr + 1] ?: 0) shl 8)
    override fun write16(addr: Int, value: Int) {
        memory[addr]     = value and 0xFF
        memory[addr + 1] = (value ushr 8) and 0xFF
    }

    fun setSecurityKey(key: Int) {
        write32(sb2Base + 0xF20, key)
    }

    fun setSlotRaw(index: Int, itemId: Int, encQty: Int) {
        val addr = sb1Base + 0x310 + index * 4
        write16(addr, itemId)
        write16(addr + 2, encQty)
    }

    fun rawQty(index: Int): Int = read16(sb1Base + 0x310 + index * 4 + 2)
    fun itemId(index: Int): Int = read16(sb1Base + 0x310 + index * 4)
}

class RareCandyShopTest {

    @Test fun emptyBag_writesNewStackInFirstSlot() {
        val bus = FakeBus()
        bus.setSecurityKey(0x1234_5678)
        val r = RareCandyShop.addRareCandy(bus, 5)
        assertEquals(RareCandyShop.Result.Ok, r)
        assertEquals(RareCandyShop.ITEM_RARE_CANDY, bus.itemId(0))
        // Stored quantity is XOR'd with low 16 of the key.
        assertEquals(5 xor 0x5678, bus.rawQty(0))
    }

    @Test fun zeroSecurityKey_storesPlaintextQty() {
        val bus = FakeBus()
        bus.setSecurityKey(0)
        RareCandyShop.addRareCandy(bus, 7)
        assertEquals(7, bus.rawQty(0))
    }

    @Test fun existingStack_topsUp_andRespectsKey() {
        val bus = FakeBus()
        val key16 = 0xABCD
        bus.setSecurityKey(key16)
        // Slot 3 already holds 12 Rare Candies.
        bus.setSlotRaw(3, RareCandyShop.ITEM_RARE_CANDY, 12 xor key16)
        val r = RareCandyShop.addRareCandy(bus, 3)
        assertEquals(RareCandyShop.Result.Ok, r)
        // Original slot still has the right item id and the new stack count.
        assertEquals(RareCandyShop.ITEM_RARE_CANDY, bus.itemId(3))
        assertEquals(15 xor key16, bus.rawQty(3))
        // No new slot allocated.
        assertEquals(RareCandyShop.ITEM_NONE, bus.itemId(0))
    }

    @Test fun existingStack_overflowingFails_withoutMutating() {
        val bus = FakeBus()
        val key16 = 0x4242
        bus.setSecurityKey(key16)
        bus.setSlotRaw(0, RareCandyShop.ITEM_RARE_CANDY, 998 xor key16)
        val r = RareCandyShop.addRareCandy(bus, 5)
        assertTrue(r is RareCandyShop.Result.StackOverflow)
        assertEquals(998 xor key16, bus.rawQty(0))   // unchanged
    }

    @Test fun nonRareCandyItem_isNotDisturbedByLookupOrInsert() {
        val bus = FakeBus()
        bus.setSecurityKey(0)
        // A Potion (item id 13) lives in slot 0; rare candy should land at slot 1.
        bus.setSlotRaw(0, 13, 4)
        val r = RareCandyShop.addRareCandy(bus, 2)
        assertEquals(RareCandyShop.Result.Ok, r)
        assertEquals(13, bus.itemId(0))
        assertEquals(4, bus.rawQty(0))
        assertEquals(RareCandyShop.ITEM_RARE_CANDY, bus.itemId(1))
        assertEquals(2, bus.rawQty(1))
    }

    @Test fun bagFull_andNoMatch_returnsBagFull() {
        val bus = FakeBus()
        bus.setSecurityKey(0)
        // Fill all 42 slots with a non-RC item.
        for (i in 0 until RareCandyShop.BAG_ITEMS_COUNT) {
            bus.setSlotRaw(i, 13, 1)
        }
        val r = RareCandyShop.addRareCandy(bus, 1)
        assertEquals(RareCandyShop.Result.BagFull, r)
    }

    @Test fun bagFullButHasMatchingStack_stillTopsUp() {
        val bus = FakeBus()
        val key16 = 0xBEEF
        bus.setSecurityKey(key16)
        for (i in 0 until RareCandyShop.BAG_ITEMS_COUNT - 1) {
            bus.setSlotRaw(i, 13, 1)
        }
        bus.setSlotRaw(
            RareCandyShop.BAG_ITEMS_COUNT - 1,
            RareCandyShop.ITEM_RARE_CANDY,
            10 xor key16,
        )
        val r = RareCandyShop.addRareCandy(bus, 4)
        assertEquals(RareCandyShop.Result.Ok, r)
        assertEquals(14 xor key16, bus.rawQty(RareCandyShop.BAG_ITEMS_COUNT - 1))
    }

    @Test fun uninitializedSaveBlockPointer_returnsNotInGame() {
        val bus = FakeBus()
        bus.write32(0x03005008, 0)              // SB1 ptr null → title screen
        val r = RareCandyShop.addRareCandy(bus, 1)
        assertEquals(RareCandyShop.Result.NotInGame, r)
    }
}

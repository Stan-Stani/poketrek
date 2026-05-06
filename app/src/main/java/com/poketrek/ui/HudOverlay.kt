package com.poketrek.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.poketrek.emu.EmulatorRunner
import com.poketrek.emu.MovementGate
import com.poketrek.emu.RomCalibrator
import com.poketrek.emu.RomIdentity
import com.poketrek.emu.RomVariant
import com.poketrek.moneo.MoneoModule
import com.poketrek.step.MAX_RARE_CANDY_COST
import com.poketrek.step.MIN_RARE_CANDY_COST
import com.poketrek.step.MovementBudget
import com.poketrek.step.parseRatioInput
import kotlinx.coroutines.launch

/**
 * Discrete ratio steps the slider snaps through. Index 0 is the hardest
 * (most real steps per tile); the last index is the easiest. The middle
 * stop is realistic 1:1.
 */
private val RATIO_TABLE: List<Pair<Int, Int>> = listOf(
    1 to 8, 1 to 6, 1 to 4, 1 to 3, 1 to 2,
    1 to 1,
    2 to 1, 3 to 1, 4 to 1, 6 to 1, 8 to 1, 12 to 1, 16 to 1,
)

private fun ratioIndexFor(num: Int, den: Int): Int {
    val exact = RATIO_TABLE.indexOfFirst { it.first == num && it.second == den }
    if (exact >= 0) return exact
    // Custom-set ratio not in the preset table — snap to the closest preset
    // by tile-per-step value so the slider doesn't surprise-jump to 1:1.
    val target = num.toDouble() / den.toDouble()
    return RATIO_TABLE.indices.minByOrNull { i ->
        val (n, d) = RATIO_TABLE[i]
        kotlin.math.abs(n.toDouble() / d - target)
    } ?: RATIO_TABLE.indexOfFirst { it.first == 1 && it.second == 1 }
}

private fun ratioMatchesPreset(num: Int, den: Int): Boolean =
    RATIO_TABLE.any { it.first == num && it.second == den }

private fun describeRatio(num: Int, den: Int): String = when {
    num == 1 && den == 1 -> "1 step = 1 tile (realistic)"
    num >= den -> {
        val tiles = num / den
        "1 step = $tiles tile${if (tiles != 1) "s" else ""}"
    }
    else -> {
        val steps = den / num
        "$steps steps = 1 tile"
    }
}

/**
 * Compact, always-visible HUD: just the tile count + a button that opens the
 * settings sheet. Sits in the corner of the framebuffer letterbox so it
 * doesn't overlap gameplay.
 */
@Composable
fun HudBadge(
    budget: MovementBudget,
    romIdentity: com.poketrek.emu.RomIdentity?,
    hasCalibration: Boolean,
    onOpenSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val tiles by budget.budget.collectAsState()
    val gateOn by budget.gateEnabled.collectAsState()
    // Warn whenever no calibration is loaded — that's the actual condition
    // the run loop checks before gating. The variant's static
    // `gatingSupported` flag only says "ships pre-calibrated"; a Korean ROM
    // becomes gateable as soon as the user runs the calibration flow.
    val warn = romIdentity != null && !hasCalibration
    Row(
        modifier = modifier
            .background(Color(0xCC000000), shape = RoundedCornerShape(10.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Column {
            Text(
                text = if (gateOn) "TILES $tiles" else "TILES $tiles (free)",
                color = if (gateOn && tiles == 0) Color(0xFFEF4444) else Color.White,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold,
                fontSize = 13.sp,
            )
            if (warn) {
                Text(
                    text = "⚠ ${romIdentity!!.variant.displayName} — gating off",
                    color = Color(0xFFFBBF24),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 9.sp,
                )
            }
        }
        Button(
            onClick = onOpenSettings,
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF374151)),
            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
        ) {
            Text("☰", color = Color.White, fontSize = 13.sp)
        }
    }
}

/**
 * Floating reminder rendered while a calibration baseline is captured but not
 * yet completed. The settings sheet is dismissed after baseline capture so the
 * player can walk one tile in the overworld; this chip nudges them back.
 */
@Composable
fun CalibrationPendingChip(
    onOpenSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .background(Color(0xCC92400E), shape = RoundedCornerShape(10.dp))
            .padding(horizontal = 10.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(
            "Walk 1 tile, then capture",
            color = Color.White,
            fontFamily = FontFamily.Monospace,
            fontSize = 11.sp,
        )
        Button(
            onClick = onOpenSettings,
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF111827)),
            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
        ) {
            Text("Capture", color = Color.White, fontSize = 11.sp)
        }
    }
}

/**
 * Lightweight read-only debug overlay: shows the RAM probe snapshot. Only
 * rendered when the user has enabled the debug HUD in settings. Designed to
 * sit somewhere unobtrusive (top-center letterbox).
 */
@Composable
fun DebugOverlay(
    snapshot: com.poketrek.emu.LeafGreenRam.Snapshot?,
    romIdentity: com.poketrek.emu.RomIdentity?,
    onDebugAddSteps: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier
            .background(Color(0xCC000000), shape = RoundedCornerShape(8.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        if (romIdentity != null) {
            Text(
                text = "ROM: ${romIdentity.variant.displayName} ${romIdentity.crc32Hex}",
                color = Color(0xFF9CA3AF),
                fontFamily = FontFamily.Monospace,
                fontSize = 10.sp,
            )
        }
        if (snapshot != null) {
            Text(
                text = formatSnapshot(snapshot),
                color = Color(0xFF9CA3AF),
                fontFamily = FontFamily.Monospace,
                fontSize = 10.sp,
            )
        }
        Button(
            onClick = { onDebugAddSteps(10) },
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF6366F1)),
            contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
        ) {
            Text("+10 fake steps", color = Color.White, fontSize = 11.sp)
        }
    }
}

/**
 * Modal bottom sheet with all user-tweakable knobs. Hidden by default; opened
 * from the HUD badge.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsSheet(
    budget: MovementBudget,
    gate: MovementGate,
    romIdentity: RomIdentity?,
    onDismiss: () -> Unit,
    onPickRom: () -> Unit,
    getSaveSlots: () -> List<com.poketrek.emu.SaveStateStore.Slot>,
    onSaveSlot: (Int) -> Boolean,
    onLoadSlot: (Int) -> Boolean,
    onBuyRareCandy: (Int) -> EmulatorRunner.BuyResult,
    hasCalibration: Boolean,
    hasPendingBaseline: Boolean,
    calibrationStatus: RomCalibrator.Result?,
    onBeginCalibration: () -> Boolean,
    onFinishCalibration: suspend () -> RomCalibrator.Result,
    onCancelCalibration: () -> Unit,
    onClearCalibrationStatus: () -> Unit,
    moneo: MoneoModule,
    onOpenMoneo: () -> Unit,
    getRomLibrary: () -> List<com.poketrek.emu.RomCache.Slot> = { emptyList() },
    currentRomCrc32: () -> Long? = { null },
    onLoadCachedRom: (Long) -> Boolean = { false },
    onRemoveCachedRom: (Long) -> Unit = {},
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val tiles by budget.budget.collectAsState()
    val ratioNum by budget.tilesPerStepNum.collectAsState()
    val ratioDen by budget.tilesPerStepDen.collectAsState()
    val gateOn by budget.gateEnabled.collectAsState()
    val debugOn by budget.debugHudVisible.collectAsState()
    val hapticOn by budget.hapticOnStep.collectAsState()
    val currentIndex = ratioIndexFor(ratioNum, ratioDen)
    var ratioDraft by remember(currentIndex) { mutableStateOf(currentIndex.toFloat()) }
    val draftIndex = ratioDraft.toInt().coerceIn(0, RATIO_TABLE.lastIndex)
    val (draftNum, draftDen) = RATIO_TABLE[draftIndex]

    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 24.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("PokéTrek settings", fontWeight = FontWeight.Bold, fontSize = 18.sp)
                Button(
                    onClick = { onPickRom(); onDismiss() },
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp),
                ) {
                    Text("Add ROM…", fontSize = 12.sp)
                }
            }

            var romLibrary by remember { mutableStateOf(getRomLibrary()) }
            RomLibrarySection(
                slots = romLibrary,
                currentCrc32 = currentRomCrc32(),
                onLoad = { crc -> if (onLoadCachedRom(crc)) onDismiss() },
                onRemove = { crc ->
                    onRemoveCachedRom(crc)
                    romLibrary = getRomLibrary()
                },
            )

            ToggleRow(
                label = "Step gate",
                sublabel = if (gateOn) "Movement requires real steps" else "Free walking",
                checked = gateOn,
                onCheckedChange = { gate.setEnabled(it) },
            )

            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                val isCustom = !ratioMatchesPreset(ratioNum, ratioDen)
                Text(
                    if (isCustom) "Custom: ${describeRatio(ratioNum, ratioDen)}"
                    else describeRatio(draftNum, draftDen),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 14.sp,
                )
                Slider(
                    value = ratioDraft,
                    onValueChange = { ratioDraft = it },
                    onValueChangeFinished = {
                        val (n, d) = RATIO_TABLE[draftIndex]
                        budget.setRatio(n, d)
                    },
                    valueRange = 0f..(RATIO_TABLE.lastIndex).toFloat(),
                    steps = RATIO_TABLE.size - 2,
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(
                        "8 steps / tile",
                        color = Color(0xFF6B7280),
                        fontSize = 11.sp,
                    )
                    Text(
                        "16 tiles / step",
                        color = Color(0xFF6B7280),
                        fontSize = 11.sp,
                    )
                }
            }

            CustomRatioRow(
                currentNum = ratioNum,
                currentDen = ratioDen,
                onApply = { n, d -> budget.setRatio(n, d) },
            )

            Text(
                "Current budget: $tiles tiles",
                color = Color(0xFF6B7280),
                fontFamily = FontFamily.Monospace,
                fontSize = 12.sp,
            )

            ToggleRow(
                label = "Vibrate on step credit",
                sublabel = "Brief pulse when a real step adds to your tile budget",
                checked = hapticOn,
                onCheckedChange = { budget.setHapticOnStep(it) },
            )

            ToggleRow(
                label = "Debug overlay",
                sublabel = "Shows RAM probe + fake-step button",
                checked = debugOn,
                onCheckedChange = { budget.setDebugHudVisible(it) },
            )

            Spacer(Modifier.height(4.dp))
            MoneoSection(
                moneo = moneo,
                onOpenMoneo = { onOpenMoneo(); onDismiss() },
            )

            if (romIdentity?.variant == RomVariant.LEAFGREEN_US_REV1) {
                Spacer(Modifier.height(4.dp))
                ShopSection(
                    budget = budget,
                    onBuyRareCandy = onBuyRareCandy,
                )
            }

            if (romIdentity != null) {
                Spacer(Modifier.height(4.dp))
                CalibrationSection(
                    hasCalibration = hasCalibration,
                    hasPendingBaseline = hasPendingBaseline,
                    status = calibrationStatus,
                    romIdentity = romIdentity,
                    onBeginCalibration = {
                        if (onBeginCalibration()) onDismiss()
                    },
                    onFinishCalibration = onFinishCalibration,
                    onCancelCalibration = onCancelCalibration,
                    onClearStatus = onClearCalibrationStatus,
                )
            }

            Spacer(Modifier.height(4.dp))
            AdvancedSection(
                onResetSteps = { budget.resetBudgetAndRebaseSteps() },
            )

            Spacer(Modifier.height(4.dp))
            Text("Save states", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            var slotsVersion by remember { mutableStateOf(0) }
            val slots = remember(slotsVersion) { getSaveSlots() }
            slots.forEach { slot ->
                SlotRow(
                    slot = slot,
                    currentRomCrc = romIdentity?.crc32,
                    onSave = {
                        if (onSaveSlot(slot.index)) slotsVersion++
                    },
                    onLoad = {
                        if (onLoadSlot(slot.index)) onDismiss()
                    },
                )
            }
            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun SlotRow(
    slot: com.poketrek.emu.SaveStateStore.Slot,
    currentRomCrc: Long?,
    onSave: () -> Unit,
    onLoad: () -> Unit,
) {
    val mismatch = slot.romCrc32 != null
        && currentRomCrc != null
        && slot.romCrc32 != currentRomCrc
    val romLabel = when {
        slot.isEmpty -> null
        slot.romCrc32 == null -> "Unknown ROM"
        else -> {
            val v = RomIdentity.variantFor(slot.romCrc32)
            "${v.displayName} ${RomIdentity.crc32Hex(slot.romCrc32)}"
        }
    }
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Column(Modifier.weight(1f)) {
            Text("Slot ${slot.index}", fontWeight = FontWeight.SemiBold, fontSize = 13.sp)
            Text(
                if (slot.isEmpty) "Empty" else relativeTime(slot.savedAt!!),
                color = Color(0xFF6B7280),
                fontSize = 11.sp,
            )
            romLabel?.let {
                Text(
                    text = if (mismatch) "$it  ⚠ different ROM" else it,
                    color = if (mismatch) Color(0xFFEF4444) else Color(0xFF6B7280),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 10.sp,
                )
            }
        }
        Button(onClick = onSave, contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp)) {
            Text("Save", fontSize = 12.sp)
        }
        Button(
            onClick = onLoad,
            enabled = !slot.isEmpty && !mismatch,
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp),
        ) {
            Text("Load", fontSize = 12.sp)
        }
    }
}

private fun relativeTime(epochMs: Long): String {
    val cs = android.text.format.DateUtils.getRelativeTimeSpanString(
        epochMs,
        System.currentTimeMillis(),
        android.text.format.DateUtils.MINUTE_IN_MILLIS,
        android.text.format.DateUtils.FORMAT_ABBREV_RELATIVE,
    )
    return cs?.toString() ?: "unknown"
}

@Composable
private fun ToggleRow(
    label: String,
    sublabel: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f)) {
            Text(label, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            Text(sublabel, color = Color(0xFF6B7280), fontSize = 12.sp)
        }
        Spacer(Modifier.width(8.dp))
        Switch(
            checked = checked,
            onCheckedChange = onCheckedChange,
            colors = SwitchDefaults.colors(),
        )
    }
}

private fun formatSnapshot(s: com.poketrek.emu.LeafGreenRam.Snapshot): String {
    fun hex(v: Int, width: Int) = "0x" + v.toUInt().toString(16).padStart(width, '0').uppercase()
    return "X:${s.playerX} Y:${s.playerY} bank:${s.mapBank}/${s.mapId} mov:${s.movingStatus} sb1=${hex(s.saveBlockPtr, 8)}"
}

/**
 * Free-form ratio input: accepts integers, decimals, or fractions and applies
 * via [parseRatioInput]. Sits below the discrete preset slider; the slider
 * snaps to the closest preset when a non-preset value is set here.
 */
@Composable
private fun CustomRatioRow(
    currentNum: Int,
    currentDen: Int,
    onApply: (num: Int, den: Int) -> Unit,
) {
    var draft by remember(currentNum, currentDen) {
        mutableStateOf(if (currentDen == 1) "$currentNum" else "$currentNum/$currentDen")
    }
    val parsed = parseRatioInput(draft)
    val isError = draft.isNotBlank() && parsed == null
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        OutlinedTextField(
            value = draft,
            onValueChange = { draft = it },
            modifier = Modifier.weight(1f),
            label = { Text("Custom ratio (e.g. 2.5 or 5/2)", fontSize = 11.sp) },
            singleLine = true,
            isError = isError,
            keyboardOptions = KeyboardOptions(
                keyboardType = KeyboardType.Decimal,
                imeAction = ImeAction.Done,
            ),
            keyboardActions = KeyboardActions(
                onDone = { parsed?.let { (n, d) -> onApply(n, d) } },
            ),
        )
        Button(
            onClick = { parsed?.let { (n, d) -> onApply(n, d) } },
            enabled = parsed != null && parsed != (currentNum to currentDen),
            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 0.dp),
        ) {
            Text("Set", fontSize = 12.sp)
        }
    }
}

/**
 * Collapsible "Advanced / debug" section. Hidden by default to keep the
 * primary settings sheet calm; expand to reveal destructive actions.
 */
@Composable
private fun AdvancedSection(
    onResetSteps: () -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    var confirmReset by remember { mutableStateOf(false) }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier
                .fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("Advanced", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            TextButton(
                onClick = { expanded = !expanded },
                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
            ) {
                Text(if (expanded) "Hide" else "Show", fontSize = 12.sp)
            }
        }
        if (expanded) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(Modifier.weight(1f)) {
                    Text("Reset budget & step baseline", fontSize = 13.sp)
                    Text(
                        "Zeros tiles, clears carry, and rebases the step counter so future steps count from now.",
                        color = Color(0xFF6B7280),
                        fontSize = 11.sp,
                    )
                }
                Spacer(Modifier.width(8.dp))
                Button(
                    onClick = { confirmReset = true },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFB91C1C)),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp),
                ) {
                    Text("Reset", fontSize = 12.sp)
                }
            }
        }
    }

    if (confirmReset) {
        AlertDialog(
            onDismissRequest = { confirmReset = false },
            title = { Text("Reset budget?") },
            text = {
                Text(
                    "This zeros your tile budget and forgets all previously-walked steps. " +
                        "Settings, save states, and ROM are not affected.",
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    confirmReset = false
                    onResetSteps()
                }) { Text("Reset") }
            },
            dismissButton = {
                TextButton(onClick = { confirmReset = false }) { Text("Cancel") }
            },
        )
    }
}

/**
 * Collapsible "Shop" section. Spends tiles to mint Rare Candies into the
 * bag. Only shown for the calibrated US Rev 1 ROM — the bag-pocket and
 * encryption-key offsets are FRLG-specific and would corrupt other builds.
 */
@Composable
private fun ShopSection(
    budget: MovementBudget,
    onBuyRareCandy: (Int) -> EmulatorRunner.BuyResult,
) {
    val tiles by budget.budget.collectAsState()
    val cost by budget.rareCandyCost.collectAsState()
    var expanded by remember { mutableStateOf(false) }
    var costDraft by remember(cost) { mutableStateOf(cost.toString()) }
    var quantity by remember { mutableStateOf(1) }
    var feedback by remember { mutableStateOf<String?>(null) }
    val parsedCost = costDraft.trim().toIntOrNull()
        ?.takeIf { it in MIN_RARE_CANDY_COST..MAX_RARE_CANDY_COST }
    val totalCost = cost.toLong() * quantity.toLong()
    val canAfford = totalCost <= tiles
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text("Shop", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            TextButton(
                onClick = { expanded = !expanded },
                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
            ) {
                Text(if (expanded) "Hide" else "Show", fontSize = 12.sp)
            }
        }
        if (expanded) {
            Text(
                "Spend tiles for in-game items. Writes directly to the bag's items pocket.",
                color = Color(0xFF6B7280),
                fontSize = 11.sp,
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                OutlinedTextField(
                    value = costDraft,
                    onValueChange = { costDraft = it.filter(Char::isDigit).take(6) },
                    modifier = Modifier.weight(1f),
                    label = { Text("Tiles per Rare Candy", fontSize = 11.sp) },
                    singleLine = true,
                    isError = costDraft.isNotBlank() && parsedCost == null,
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Number,
                        imeAction = ImeAction.Done,
                    ),
                    keyboardActions = KeyboardActions(
                        onDone = { parsedCost?.let { budget.setRareCandyCost(it) } },
                    ),
                )
                Button(
                    onClick = { parsedCost?.let { budget.setRareCandyCost(it) } },
                    enabled = parsedCost != null && parsedCost != cost,
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp),
                ) {
                    Text("Set", fontSize = 12.sp)
                }
            }
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Column(Modifier.weight(1f)) {
                    Text("Rare Candy × $quantity", fontSize = 13.sp)
                    Text(
                        "Cost: $totalCost tiles",
                        color = if (canAfford) Color(0xFF6B7280) else Color(0xFFEF4444),
                        fontFamily = FontFamily.Monospace,
                        fontSize = 11.sp,
                    )
                }
                Button(
                    onClick = { if (quantity > 1) quantity-- },
                    enabled = quantity > 1,
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 0.dp),
                ) { Text("−", fontSize = 14.sp) }
                Text(
                    "$quantity",
                    fontFamily = FontFamily.Monospace,
                    fontSize = 14.sp,
                    modifier = Modifier.width(28.dp),
                )
                Button(
                    onClick = { if (quantity < 999) quantity++ },
                    enabled = quantity < 999,
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 0.dp),
                ) { Text("+", fontSize = 14.sp) }
            }
            Button(
                onClick = {
                    feedback = when (val r = onBuyRareCandy(quantity)) {
                        EmulatorRunner.BuyResult.Ok ->
                            "Bought $quantity Rare Cand${if (quantity == 1) "y" else "ies"}."
                        EmulatorRunner.BuyResult.NotEnoughTiles -> "Not enough tiles."
                        EmulatorRunner.BuyResult.UnsupportedRom -> "Shop disabled on this ROM."
                        EmulatorRunner.BuyResult.NotInGame ->
                            "Save the game once before buying — bag isn't initialized yet."
                        EmulatorRunner.BuyResult.BagFull -> "Bag is full."
                        is EmulatorRunner.BuyResult.StackWouldOverflow ->
                            "Stack would exceed 999 (have ${r.existing})."
                    }
                },
                enabled = canAfford,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF059669)),
            ) {
                Text("Buy", fontSize = 13.sp)
            }
            feedback?.let {
                Text(
                    it,
                    color = Color(0xFF6B7280),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.sp,
                )
            }
        }
    }
}
@Composable
private fun CalibrationSection(
    hasCalibration: Boolean,
    hasPendingBaseline: Boolean,
    status: com.poketrek.emu.RomCalibrator.Result?,
    romIdentity: com.poketrek.emu.RomIdentity,
    onBeginCalibration: () -> Unit,
    onFinishCalibration: suspend () -> com.poketrek.emu.RomCalibrator.Result,
    onCancelCalibration: () -> Unit,
    onClearStatus: () -> Unit,
) {
    var capturing by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("ROM Calibration", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)

        when {
            status is com.poketrek.emu.RomCalibrator.Result.Ok -> {
                Text("Calibration saved.", color = Color(0xFF059669), fontSize = 12.sp)
                Text(
                    "SaveBlock1 ptr: 0x${status.saveBlock1PtrAddr.toUInt().toString(16).uppercase()}",
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.sp,
                )
                Button(onClick = onClearStatus) { Text("OK") }
            }
            status != null -> {
                Text("Calibration failed.", color = Color(0xFFB91C1C), fontSize = 12.sp)
                Text(formatCalibrationError(status), fontSize = 11.sp, color = Color(0xFF6B7280))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = {
                        onClearStatus()
                        onBeginCalibration()
                    }) { Text("Try again") }
                    TextButton(onClick = onClearStatus) { Text("Dismiss") }
                }
            }
            capturing -> {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        strokeWidth = 2.dp,
                    )
                    Text("Scanning EWRAM…", fontSize = 12.sp)
                }
            }
            hasPendingBaseline -> {
                Text(
                    "Baseline taken. Walk exactly one tile in the overworld, then tap Capture.",
                    color = Color(0xFFD97706),
                    fontSize = 12.sp,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = {
                        capturing = true
                        scope.launch {
                            try {
                                onFinishCalibration()
                            } finally {
                                capturing = false
                            }
                        }
                    }) { Text("Capture") }
                    TextButton(onClick = onCancelCalibration) { Text("Cancel") }
                }
            }
            else -> {
                Text(
                    text = if (hasCalibration)
                        "Calibrated for ${romIdentity.crc32Hex} ✓"
                    else
                        "Not calibrated — step gating disabled for this ROM.",
                    color = if (hasCalibration) Color(0xFF059669) else Color(0xFFD97706),
                    fontSize = 12.sp,
                )
                Text(
                    "Stand still in the overworld, then tap below — the menu closes so you can walk one tile.",
                    color = Color(0xFF6B7280),
                    fontSize = 11.sp,
                )
                Button(onClick = onBeginCalibration) {
                    Text(if (hasCalibration) "Re-calibrate" else "Calibrate")
                }
            }
        }
    }
}

private fun formatCalibrationError(r: com.poketrek.emu.RomCalibrator.Result?): String = when (r) {
    is com.poketrek.emu.RomCalibrator.Result.NoChangedHalfword -> "No coordinate change detected. Did you walk exactly one tile? Make sure you took the baseline while standing still."
    is com.poketrek.emu.RomCalibrator.Result.TooManyChangedHalfwords -> "Too noisy (${r.count} candidates). Try again from a quieter game state — minimize NPCs/animations on screen."
    is com.poketrek.emu.RomCalibrator.Result.NoPointerFound -> "Found a coordinate change but no IWRAM pointer references it. Unexpected — please report."
    is com.poketrek.emu.RomCalibrator.Result.MultiplePointers -> "Ambiguous: ${r.addrs.size} candidate pointers. Try recalibrating after a save+reload."
    com.poketrek.emu.RomCalibrator.Result.ReadFailed -> "Memory read failed (no ROM loaded?)."
    else -> "Unknown failure."
}

/**
 * Small Settings-sheet section for the Moneo (Korean learning) feature.
 * Shows enable toggle, current target area, and an "Open Moneo" button.
 * Anything more advanced lives in the dedicated [com.poketrek.moneo.ui.MoneoOverlay].
 */
@Composable
private fun MoneoSection(
    moneo: MoneoModule,
    onOpenMoneo: () -> Unit,
) {
    val enabled by moneo.prefs.enabled.collectAsState()
    val targetAreaId by moneo.prefs.targetAreaId.collectAsState()
    val areas by moneo.repository.areas.collectAsState()
    val cards by moneo.repository.cards.collectAsState()
    val targetArea = areas.firstOrNull { it.id == targetAreaId }
    @Suppress("UNUSED_VARIABLE") val tick = cards
    val totalDue = moneo.repository.totalDueCount()

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text("Moneo · 몬어 (Korean)", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
        ToggleRow(
            label = "Korean learning mode",
            sublabel = if (enabled) "Review badge visible during play" else "Hidden",
            checked = enabled,
            onCheckedChange = { moneo.prefs.setEnabled(it) },
        )
        val verbatimSentences by moneo.prefs.verbatimSentences.collectAsState()
        ToggleRow(
            label = "Verbatim ROM examples",
            sublabel = if (verbatimSentences)
                "Reviews show real game lines (may spoil dialog/Pokédex)"
            else
                "Reviews show plain study sentences (no spoilers)",
            checked = verbatimSentences,
            onCheckedChange = { moneo.prefs.setVerbatimSentences(it) },
        )
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    if (targetArea != null) "Studying: ${targetArea.koreanLabel} · ${targetArea.englishName}"
                    else "No area selected",
                    fontSize = 13.sp,
                )
                Text(
                    "$totalDue card${if (totalDue == 1) "" else "s"} due across all areas",
                    color = Color(0xFF6B7280),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.sp,
                )
            }
            Spacer(Modifier.width(8.dp))
            Button(
                onClick = onOpenMoneo,
                contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp),
            ) { Text("Open", fontSize = 12.sp) }
        }

        // --- Dev: runtime EWRAM text capture (Phase 2 corpus path) -------------
        val capture = moneo.ramCapture
        if (capture != null) {
            val captureOn by capture.enabled.collectAsState()
            val runs by capture.runsCaptured.collectAsState()
            ToggleRow(
                label = "Capture runtime text (dev)",
                sublabel = if (captureOn)
                    "Sampling EWRAM diffs · $runs run${if (runs == 1) "" else "s"} captured"
                else
                    "Records candidate Korean strings to filesDir/moneo/capture.bin",
                checked = captureOn,
                onCheckedChange = { capture.setEnabled(it) },
            )
            if (runs > 0) {
                Text(
                    "Capture file: ${capture.captureSizeBytes()} bytes",
                    color = Color(0xFF6B7280),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 10.sp,
                )
                TextButton(
                    onClick = { capture.resetCapture() },
                    contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
                ) { Text("Reset capture", fontSize = 11.sp) }
            }
            // Probe button: read gStringVar1-4 synchronously and log to Logcat
            // tag "MoneoProbe". Take a screenshot at the same time to correlate
            // hex bytes → on-screen Hangul characters (charmap derivation).
            var probeResult by remember { mutableStateOf("") }
            val scope = rememberCoroutineScope()
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Button(
                    onClick = {
                        scope.launch(kotlinx.coroutines.Dispatchers.Default) {
                            val result = capture.probeTextBuffers()
                            val summary = result.entries.joinToString("\n") { (k, v) ->
                                "$k: ${v?.take(60) ?: "(null)"}"
                            }
                            probeResult = summary
                        }
                    },
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp),
                ) { Text("Probe gStringVar1-4", fontSize = 11.sp) }
                Text(
                    "→ also in Logcat tag MoneoProbe",
                    color = Color(0xFF6B7280),
                    fontSize = 10.sp,
                )
            }
            // Decode visible Korean text via VramTextReader + KoreanCharmap.
            var decodeResult by remember { mutableStateOf("") }
            val ctx = androidx.compose.ui.platform.LocalContext.current
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Button(
                    onClick = {
                        scope.launch(kotlinx.coroutines.Dispatchers.Default) {
                            val charmap = com.poketrek.moneo.corpus.KoreanCharmap.get(ctx)
                            val lines = capture.decodeVisibleText(charmap)
                            decodeResult = if (lines.isEmpty()) "(no text)"
                            else lines.joinToString("\n")
                            android.util.Log.i("MoneoProbe", "DecodeKO:\n$decodeResult")
                        }
                    },
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 0.dp),
                ) { Text("Decode KO", fontSize = 11.sp) }
                Text(
                    "(${decodeResult.lines().size} lines)",
                    color = Color(0xFF6B7280),
                    fontSize = 10.sp,
                )
            }
            if (decodeResult.isNotEmpty()) {
                Text(
                    decodeResult,
                    color = Color(0xFFFFE0B0),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 11.sp,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            if (probeResult.isNotEmpty()) {
                Text(
                    probeResult,
                    color = Color(0xFFE0E0E0),
                    fontFamily = FontFamily.Monospace,
                    fontSize = 9.sp,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

/**
 * ROM library: clickable rows for each cached ROM, current one highlighted.
 * Hidden when nothing has been cached yet (first launch).
 */
@Composable
private fun RomLibrarySection(
    slots: List<com.poketrek.emu.RomCache.Slot>,
    currentCrc32: Long?,
    onLoad: (Long) -> Unit,
    onRemove: (Long) -> Unit,
) {
    if (slots.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(
            "ROM library",
            color = Color(0xFF6B7280),
            fontSize = 11.sp,
        )
        for (slot in slots) {
            val isCurrent = slot.crc32 == currentCrc32
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        color = if (isCurrent) Color(0xFF1F3A2E) else Color(0xFF1F2937),
                        shape = RoundedCornerShape(8.dp),
                    )
                    .clickable(enabled = !isCurrent) { onLoad(slot.crc32) }
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        slot.label,
                        color = Color.White,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 13.sp,
                    )
                    Text(
                        if (isCurrent) "Loaded · ${slot.sizeBytes / 1024} KB"
                        else "${slot.sizeBytes / 1024} KB",
                        color = if (isCurrent) Color(0xFF6EE7B7) else Color(0xFF9CA3AF),
                        fontFamily = FontFamily.Monospace,
                        fontSize = 10.sp,
                    )
                }
                if (!isCurrent) {
                    TextButton(
                        onClick = { onRemove(slot.crc32) },
                        contentPadding = PaddingValues(horizontal = 8.dp, vertical = 0.dp),
                    ) {
                        Text("Remove", color = Color(0xFFEF4444), fontSize = 11.sp)
                    }
                }
            }
        }
    }
}
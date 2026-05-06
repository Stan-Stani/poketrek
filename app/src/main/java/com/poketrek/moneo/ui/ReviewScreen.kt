package com.poketrek.moneo.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.poketrek.moneo.MoneoModule
import com.poketrek.moneo.data.CardRecord
import com.poketrek.moneo.data.SentenceEntry
import com.poketrek.moneo.data.VocabEntry
import com.poketrek.moneo.srs.CardSnapshot
import com.poketrek.moneo.srs.CardState
import com.poketrek.moneo.srs.Rating

/**
 * Per-area flashcard review. Shows one card at a time; reveal then grade.
 * On grade, requests the next due card from the repository. Empty state
 * sends the user back to the area picker.
 */
@Composable
fun ReviewScreen(
    module: MoneoModule,
    areaId: String,
    onDone: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val cards by module.repository.cards.collectAsState()
    val showRomanization by module.prefs.showRomanization.collectAsState()
    var revealed by remember(areaId) { mutableStateOf(false) }
    val verbatim by module.prefs.verbatimSentences.collectAsState()

    // Pull the next due card. We re-derive on every recomposition; the cards
    // flow ensures recomposition happens after `grade()`.
    @Suppress("UNUSED_VARIABLE") val tick = cards
    val nextPair = module.repository.nextDueCard(areaId)

    if (nextPair == null) {
        Box(modifier = modifier.padding(24.dp), contentAlignment = Alignment.Center) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                Text(
                    "✓ All caught up",
                    color = Color(0xFF10B981),
                    fontWeight = FontWeight.Bold,
                    fontSize = 22.sp,
                )
                Text(
                    "No cards due in this area right now.",
                    color = Color(0xFF9CA3AF),
                    fontSize = 13.sp,
                )
                Button(onClick = onDone) { Text("Pick another area") }
            }
        }
        return
    }

    val (record, vocab) = nextPair
    Column(
        modifier = modifier
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            StateChip(record.snapshot)
            // Toggling romanization is a small per-session preference; keep it
            // unobtrusive next to the state chip, far from the grade buttons.
            Button(
                onClick = { module.prefs.setShowRomanization(!showRomanization) },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF334155)),
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 0.dp),
            ) {
                Text(
                    if (showRomanization) "발음 ✓" else "발음 —",
                    color = Color(0xFF94A3B8),
                    fontSize = 11.sp,
                )
            }
        }
        CardFront(
            vocab = vocab,
            showRomanization = showRomanization,
            revealed = revealed,
            onTapToReveal = { if (!revealed) revealed = true },
        )
        if (revealed) {
            CardBack(vocab)
            module.repository.sentenceFor(vocab.id, preferAreaId = areaId, verbatim = verbatim)?.let { sentence ->
                SentenceCard(sentence, showRomanization)
            }
            RatingButtons(
                onGrade = { rating ->
                    module.repository.grade(vocab.id, rating)
                    revealed = false
                },
            )
        } else {
            Button(
                onClick = { revealed = true },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2563EB)),
            ) {
                Text("Reveal meaning", color = Color.White, fontSize = 14.sp)
            }
        }
    }
}

@Composable
private fun StateChip(snapshot: CardSnapshot) {
    val (label, color) = when (snapshot.state) {
        CardState.NEW -> "NEW" to Color(0xFFFBBF24)
        CardState.LEARNING -> "LEARNING" to Color(0xFFF97316)
        CardState.REVIEW -> "REVIEW · ${"%.1f".format(snapshot.intervalDays)}d" to Color(0xFF10B981)
    }
    Row(
        modifier = Modifier
            .background(Color(0xFF0F172A), shape = RoundedCornerShape(6.dp))
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            label,
            color = color,
            fontFamily = FontFamily.Monospace,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
private fun CardFront(
    vocab: VocabEntry,
    showRomanization: Boolean,
    revealed: Boolean,
    onTapToReveal: () -> Unit,
) {
    val verticalPadding = if (revealed) 12.dp else 24.dp
    val koreanSize = if (revealed) 28.sp else 36.sp
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFF1F2937), shape = RoundedCornerShape(12.dp))
            .let { if (!revealed) it.clickable { onTapToReveal() } else it }
            .padding(horizontal = 24.dp, vertical = verticalPadding),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text(
            vocab.korean,
            color = Color.White,
            fontWeight = FontWeight.Bold,
            fontSize = koreanSize,
        )
        if (showRomanization) {
            Text(
                vocab.romanization,
                color = Color(0xFF9CA3AF),
                fontFamily = FontFamily.Monospace,
                fontSize = 14.sp,
            )
        }
        Text(
            vocab.partOfSpeech,
            color = Color(0xFF6B7280),
            fontSize = 11.sp,
        )
        if (!revealed) {
            Text(
                "Tap card or Reveal button",
                color = Color(0xFF6B7280),
                fontSize = 10.sp,
            )
        }
    }
}

@Composable
private fun CardBack(vocab: VocabEntry) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFF064E3B), shape = RoundedCornerShape(12.dp))
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text("Meaning", color = Color(0xFF6EE7B7), fontSize = 10.sp)
        Text(
            vocab.gloss,
            color = Color.White,
            fontWeight = FontWeight.SemiBold,
            fontSize = 18.sp,
        )
        vocab.notes?.let {
            Text(it, color = Color(0xFFA7F3D0), fontSize = 12.sp)
        }
    }
}

@Composable
private fun SentenceCard(sentence: SentenceEntry, showRomanization: Boolean) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(Color(0xFF1E293B), shape = RoundedCornerShape(12.dp))
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text("Example", color = Color(0xFF93C5FD), fontSize = 10.sp)
        Text(
            sentence.korean,
            color = Color.White,
            fontWeight = FontWeight.Medium,
            fontSize = 18.sp,
        )
        if (showRomanization) {
            Text(
                sentence.romanization,
                color = Color(0xFF94A3B8),
                fontFamily = FontFamily.Monospace,
                fontSize = 12.sp,
            )
        }
        Text(sentence.gloss, color = Color(0xFFCBD5E1), fontSize = 13.sp)
    }
}

@Composable
private fun RatingButtons(onGrade: (Rating) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        RatingButton("Again", Color(0xFFB91C1C), Modifier.weight(1f)) { onGrade(Rating.AGAIN) }
        RatingButton("Hard", Color(0xFFB45309), Modifier.weight(1f)) { onGrade(Rating.HARD) }
        RatingButton("Good", Color(0xFF15803D), Modifier.weight(1f)) { onGrade(Rating.GOOD) }
        RatingButton("Easy", Color(0xFF1D4ED8), Modifier.weight(1f)) { onGrade(Rating.EASY) }
    }
}

@Composable
private fun RatingButton(
    label: String,
    color: Color,
    modifier: Modifier = Modifier,
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        modifier = modifier,
        colors = ButtonDefaults.buttonColors(containerColor = color),
        contentPadding = PaddingValues(horizontal = 4.dp, vertical = 6.dp),
    ) {
        Text(label, color = Color.White, fontSize = 12.sp)
    }
}

@Suppress("unused")
private fun CardRecord.debugLabel(): String = "$vocabId · ${snapshot.state}"
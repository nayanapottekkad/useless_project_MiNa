"""
Master Procedural Composer for TheUnnecessaryFM
Philosophy: THE NOISE IS THE INSTRUMENT, PRODUCED INTO REAL MUSIC.

Turns ANY audio recording into a punchy, enjoyable, head-nodding ~60s musical composition:
  1. Drums: Kick, snare, hi-hats, and foley chops forged from source transients.
  2. Bass: Thick, analog-saturated sub-bass fused with source low-end texture.
  3. Chords: Lush harmonic chord progressions resonated from the source audio.
  4. Melody: Memorable melodic hook played via tuned physical resonant modeling.
  5. Atmosphere: Continuous ambient recording bed with subtle sidechain ducking.
"""

from dataclasses import dataclass
import time
from typing import Any, Callable, Dict, List, Optional, Tuple
import numpy as np
from scipy import signal

from ..dsp.analysis import CompleteAnalysis
from ..dsp.autotune import auto_tune_slice, auto_tune_continuous_phrase, harmonize_vocal_slice, get_scale_midi_notes
from ..dsp.effects import (
    apply_panning,
    master_audio,
    ping_pong_delay,
    schroeder_reverb,
    soft_saturation
)
from ..dsp.filters import design_biquad_lowpass, apply_filter, resonant_filter_bank
from ..dsp.granular import create_granular_pad
from ..dsp.pitch import midi_to_hz, hz_to_midi
from ..dsp.preprocess import PreprocessedAudio
from ..dsp.segmentation import (
    AudioSlice,
    SourcePalette,
    build_source_palette,
    apply_slice_envelope,
    normalize_slice_rms,
    apply_fade,
    dehiss_audio
)
from ..dsp.synthesis import (
    render_karplus_strong_noise_note,
    render_noise_bass_note,
    render_trap_808_glide_bass,
    render_noise_downlifter,
    render_noise_hihat,
    render_noise_instrument_note,
    render_noise_kick,
    render_noise_open_hihat,
    render_noise_riser,
    render_noise_snare,
    render_pitched_vocal_chop
)
from ..utils.random import SeededRNG, generate_seed
from .artist_profiles import ArtistProfile, get_random_artist_for_genre, get_artist_by_id
from .arrangement import CompositionArrangement, Section, plan_arrangement
from .chords import select_chord_progression
from .melody import sequence_melody
from .rhythm_generator import generate_rhythm
from .scales import MusicalScale, select_scale
from .scoring import CandidateScore, score_composition


class BagSelector:
    """
    Round-robin shuffled bag selector with guaranteed no immediate repeats.
    Ensures varied selection without unnatural rapid looping or modulo repetition.
    """
    def __init__(self, items: List[Any], rng: SeededRNG):
        self.items = [x for x in items if x is not None] if items else []
        self.rng = rng
        self.pool: List[Any] = []
        self.last_item: Any = None
        self._refill()

    def _refill(self):
        if not self.items:
            return
        shuffled = self.rng.shuffle(self.items)
        if len(shuffled) > 1 and self.last_item is not None and shuffled[0] is self.last_item:
            shuffled[0], shuffled[-1] = shuffled[-1], shuffled[0]
        self.pool = shuffled

    def next(self) -> Any:
        if not self.items:
            return None
        if not self.pool:
            self._refill()
        item = self.pool.pop(0)
        self.last_item = item
        return item


@dataclass
class CompositionResult:
    audio: np.ndarray                 # Mastered stereo float32 array, shape (2, N)
    sr: int                           # 44100
    duration: float                   # ~60s (55-65s)
    seed: int                         # Seed used
    scale: MusicalScale               # Scale used
    tempo_bpm: float                  # Tempo
    arrangement: CompositionArrangement
    score: CandidateScore
    stems_info: Dict[str, str]        # Active musical stems
    palette_info: Dict[str, int]      # Slice counts per acoustic role
    artist_name: str = ""
    artist_id: str = ""
    artist_track_hint: str = ""
    cycle_reset: bool = False
    style_name: str = ""
    style_desc: str = ""
    smart_profile: Optional[Any] = None



def _tile_or_loop_bed(slices: List[AudioSlice], target_samples: int, sr: int, rng: SeededRNG) -> np.ndarray:
    """
    Creates a continuous atmospheric stereo bed traversing source slices
    chronologically across the timeline without clicks or sudden volume jumps.
    """
    if not slices:
        return np.zeros((2, target_samples), dtype=np.float32)

    bed_mono = np.zeros(target_samples, dtype=np.float32)
    cur_pos = 0
    slice_idx = 0

    # Ensure slices are traversed chronologically by start_sec
    sorted_slices = sorted(slices, key=lambda s: s.start_sec)

    while cur_pos < target_samples:
        sl = sorted_slices[slice_idx % len(sorted_slices)]
        slice_idx += 1
        s_audio = sl.audio.astype(np.float32)
        s_len = len(s_audio)
        if s_len <= 32:
            continue

        # Smooth crossfade length: proportional to slice length, up to 0.35s
        fade_len = max(128, min(int(0.35 * sr), int(s_len * 0.30)))
        t_fade = np.linspace(0.0, np.pi * 0.5, fade_len, dtype=np.float32)
        fade_in = np.sin(t_fade)
        fade_out = np.cos(t_fade)

        # Pre-window slice ends
        s_prepared = s_audio.copy()
        s_prepared[:fade_len] *= fade_in
        s_prepared[-fade_len:] *= fade_out

        end_pos = min(target_samples, cur_pos + s_len)
        write_len = end_pos - cur_pos
        if write_len <= 0:
            break

        bed_mono[cur_pos:end_pos] += s_prepared[:write_len]
        step = max(int(0.12 * sr), s_len - fade_len)
        cur_pos += step

    # Soft normalize bed and smooth beginning/end to ensure 100% zero crackle
    pk = np.max(np.abs(bed_mono))
    if pk > 1e-4:
        bed_mono = (bed_mono / pk) * 0.82

    edge_fade = min(int(0.04 * sr), target_samples // 4)
    if edge_fade > 1:
        att = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, edge_fade, dtype=np.float32))
        bed_mono[:edge_fade] *= att
        bed_mono[-edge_fade:] *= att[::-1]

    pan_offset = rng.uniform(-0.10, 0.10)
    return apply_panning(bed_mono, pan=pan_offset)


def render_candidate_composition(
    prep: PreprocessedAudio,
    analysis: CompleteAnalysis,
    seed: int,
    beat_preference: str = "pop",
    energy_preference: str = "low",
    vocal_mode: str = "auto",
    palette: Optional[SourcePalette] = None,
    shared_pad: Optional[np.ndarray] = None,
    on_progress: Optional[Any] = None,
    target_duration: float = 30.0,
    exclude_artist_ids: Optional[List[str]] = None,
    preferred_artist_id: Optional[str] = None
) -> CompositionResult:
    """
    Renders a complete musical composition (30s or 60s) with punchy beats,
    rich bass, lush chords, and a catchy melodic hook forged from the source
    recording. Each genre is sonically distinct by design.
    """
    rng = SeededRNG(seed)
    sr = prep.sr

    # 1. Multi-Scale Palette Extraction (Reused across candidates if provided)
    if palette is None:
        palette = build_source_palette(
            audio=prep.mono,
            sr=sr,
            onset_samples=analysis.rhythm.onset_samples,
            target_slice_count=48,
            smart_profile=getattr(analysis, 'smart_profile', None)
        )

    # 2. Select Iconic Artist Archetype & Musical Scale
    artist_profile, cycle_reset = get_random_artist_for_genre(
        beat_preference,
        rng=rng,
        exclude_artist_ids=exclude_artist_ids,
        preferred_artist_id=preferred_artist_id
    )
    scale = select_scale(
        brightness=analysis.spectral.brightness,
        noisiness=analysis.texture.noisiness,
        candidate_root_notes=analysis.pitch.candidate_notes,
        rng=rng,
        genre_preference=beat_preference,
        preferred_scale_types=artist_profile.preferred_scales
    )

    # 3. Select Musical Tempo (BPM tailored to Artist Profile)
    bpm = rng.uniform(artist_profile.bpm_min, artist_profile.bpm_max)
    if energy_preference == "low":
        bpm = max(55.0, bpm * 0.90)
    elif energy_preference == "high":
        bpm = min(174.0, bpm * 1.06)
    bpm = round(bpm, 1)

    # 4. Plan Adaptive Song Arrangement (target 30s or 60s based on user choice)
    arrangement = plan_arrangement(
        bpm=bpm,
        source_energy_envelope=analysis.amplitude.envelope_curve,
        sonic_character=analysis.classification,
        rng=rng,
        target_sec=target_duration,
        flow_archetype=artist_profile.arrangement_flow
    )
    total_duration = arrangement.total_duration
    total_samples = int(total_duration * sr)

    # ── Artist Archetype Sonic Parameters & Mix Settings ───────────────────────
    pref            = (beat_preference or "pop").lower()
    _lead_style     = artist_profile.lead_style
    _bass_style     = artist_profile.bass_style
    _chord_q        = artist_profile.chord_q
    _chord_reverb   = artist_profile.chord_reverb
    _melody_reverb  = artist_profile.lead_reverb
    _melody_delay   = artist_profile.lead_delay
    _bed_gain_mul   = artist_profile.bed_gain_mul
    _melody_mix     = artist_profile.melody_mix
    _chord_mix      = artist_profile.chord_mix
    _bass_mix       = artist_profile.bass_mix

    # 5. Generate Chord Progression & Melodic Hook (Genre & Artist adapted)
    chords = select_chord_progression(
        scale,
        rng=rng,
        genre_preference=beat_preference,
        progression_pool=artist_profile.progression_pool
    )
    melody_events = sequence_melody(
        scale=scale,
        total_bars=arrangement.total_bars,
        seconds_per_bar=arrangement.seconds_per_bar,
        source_peaks=analysis.spectral.dominant_frequencies,
        has_pitch=analysis.pitch.has_reliable_pitch,
        density_factor=0.65 if energy_preference == "high" else 0.50,
        rng=rng,
        genre_preference=beat_preference
    )

    # 6. Generate Punchy Drum & Percussion Rhythm
    rhythm_track = generate_rhythm(
        style_preference=beat_preference,
        bpm=bpm,
        has_source_rhythm=analysis.rhythm.has_reliable_rhythm,
        rng=rng,
        artist_profile=artist_profile
    )

    # 7. Low-Memory Direct Accumulation Mix Buffer (shape: 2, total_samples)
    mix = np.zeros((2, total_samples), dtype=np.float32)

    # 7.5. Compute Scale MIDI Notes & Retrieve Smart Source Profile
    smart_profile = getattr(analysis, 'smart_profile', None)
    scale_midis = get_scale_midi_notes(getattr(scale, 'root_name', 'C'), getattr(scale, 'intervals', [0, 2, 4, 5, 7, 9, 11]))

    is_vocal_source = bool(
        smart_profile and (
            getattr(smart_profile, 'has_speech_or_vocal', False)
            or getattr(smart_profile, 'has_humming', False)
            or getattr(smart_profile, 'primary_category', '') == "VOCAL"
        )
    )
    is_lead_vocal_mode = bool(
        is_vocal_source and (
            (vocal_mode in ("lead", "full_phrase"))
            or (vocal_mode == "auto" and len(getattr(palette, 'full_vocal_phrases', [])) > 0)
        )
    )

    # --- STEM 0: INTRO PRODUCER TAG / ANCHOR HOOK (The Psychological Anchor) ---
    # In Lead Vocal Mode: suppress intro snippet to avoid out-of-order chopped words.
    # In other modes: plays a brief, musical, filtered teaser that sweeps straight into the beat!
    intro_sec = next((s for s in arrangement.sections if "source_tag" in s.active_layers), arrangement.sections[0])
    if intro_sec and not is_lead_vocal_mode:
        # Keep anchor teaser very brief (0.8s - 1.2s max) and musical - never let raw noise play solo!
        tag_dur = min(intro_sec.duration * 0.35, 1.2)
        tag_samples = int(tag_dur * sr)
        tag_audio = None
        if not is_vocal_source:
            # If traffic horns or tonal impacts are available, use the best horn or crisp onset
            if getattr(palette, 'traffic_horns', None) and len(palette.traffic_horns[0].audio) > 0:
                tag_audio = palette.traffic_horns[0].audio[:tag_samples]
            elif palette.impacts and len(palette.impacts[0].audio) > 0:
                tag_audio = palette.impacts[0].audio[:tag_samples]
            elif len(prep.mono) >= tag_samples:
                tag_audio = prep.mono[:tag_samples]
            else:
                tag_audio = prep.mono
        else:
            _intro_phrases = getattr(palette, 'full_vocal_phrases', [])
            if _intro_phrases:
                _best_p = max(_intro_phrases, key=lambda p: p.duration)
                tag_audio = _best_p.audio
            elif palette.vocal_chops:
                tag_audio = palette.vocal_chops[0].audio
            elif len(prep.mono) >= tag_samples:
                tag_audio = prep.mono[:tag_samples]
            else:
                tag_audio = prep.mono

        if tag_audio is not None and len(tag_audio) > 0:
            clean_tag = dehiss_audio(tag_audio, sr=sr, high_cut_hz=6800.0, gate_threshold_db=-36.0)
            clean_tag = normalize_slice_rms(clean_tag, target_rms=0.10)
            # Auto-tune the intro producer tag to the song's root key if vocal/speech/hum or horn
            if smart_profile and getattr(smart_profile, 'autotune_enabled', False):
                if len(clean_tag) > int(0.4 * sr):
                    clean_tag = auto_tune_continuous_phrase(clean_tag, scale_midis=scale_midis, sr=sr, strength=1.0)
                else:
                    clean_tag, _, _ = auto_tune_slice(clean_tag, scale_midis=scale_midis, strength=1.0, sr=sr)

            tl = min(len(clean_tag), tag_samples, total_samples)
            if tl > 64:
                tag_fade_in = min(int(0.02 * sr), tl // 6)
                tag_fade_out = min(int(0.12 * sr), tl // 3)
                tag_chunk = clean_tag[:tl].copy()
                if tag_fade_in > 1:
                    tag_chunk[:tag_fade_in] *= (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, tag_fade_in, dtype=np.float32)))
                if tag_fade_out > 1:
                    t_fo = np.linspace(0, 1, tag_fade_out, dtype=np.float32)
                    tag_chunk[-tag_fade_out:] *= (1.0 - t_fo) ** 1.5

                # DJ highpass sweep into the beat
                if not is_vocal_source and tl > int(0.25 * sr):
                    try:
                        b_sw, a_sw = signal.butter(1, min(0.35, 300.0 / (sr * 0.5)), btype='high')
                        tag_chunk = signal.lfilter(b_sw, a_sw, tag_chunk)
                    except Exception:
                        pass

                tag_level = 0.32 if not is_vocal_source else 0.48
                mix[0, :tl] += tag_chunk * tag_level
                mix[1, :tl] += tag_chunk * tag_level

    # Classic vocal fusion (e.g. Lady Gaga & RedOne pop archetype from db0ee3d):
    is_classic_vocal = bool(getattr(artist_profile, 'special_flags', {}).get("classic_vocal_fusion", False)) and (vocal_mode in ("auto", "classic", "off"))

    # --- STEM 1: ATMOSPHERIC SOURCE BED (With Tempo-Synced Sidechain Pumping) ---
    # In Lead Vocal Mode: use purely non-vocal ambience/drones unless classic vocal fusion is active!
    if is_lead_vocal_mode and not is_classic_vocal:
        non_vocal = [s for s in (palette.ambience + palette.drones + palette.textures) if getattr(s, "role", "") not in ("VOCAL_PHRASE", "VOCAL_CHOP")]
        bed_source_slices = non_vocal if non_vocal else (palette.ambience or palette.drones)
    else:
        bed_source_slices = palette.chronological_slices if palette.chronological_slices else (palette.ambience or palette.drones)
    raw_bed = _tile_or_loop_bed(bed_source_slices, total_samples, sr, rng=rng)

    # CRUCIAL AUDIO POLISH FOR ENVIRONMENTAL / TRAFFIC NOISE:
    # 1. Bandpass filter to remove muddy sub-bass rumble (< 220 Hz) and harsh screech/wind (> 3000 Hz)
    try:
        nyq = sr * 0.5
        b_bp, a_bp = signal.butter(2, [220.0 / nyq, min(0.85, 3000.0 / nyq)], btype='bandpass')
        raw_bed[0] = signal.lfilter(b_bp, a_bp, raw_bed[0])
        raw_bed[1] = signal.lfilter(b_bp, a_bp, raw_bed[1])
    except Exception:
        pass

    # 2. Subtle stereo widening to keep center channel punchy and clear for kick, bass, and chords!
    d_samp = min(int(0.012 * sr), raw_bed.shape[1] - 1)
    if d_samp > 0:
        raw_bed[1, d_samp:] = 0.85 * raw_bed[1, d_samp:] + 0.15 * raw_bed[0, :-d_samp]

    bed_gain_curve = np.zeros(total_samples, dtype=np.float32)
    ramp_len = int(0.035 * sr)
    for i, sec in enumerate(arrangement.sections):
        s_start = int(sec.start_time * sr)
        s_end = min(total_samples, int((sec.start_time + sec.duration) * sr))

        # Bed must be a subtle, warm background texture (gain: 0.03 to 0.055), NEVER a loud roaring traffic wash!
        # In drops/choruses (high energy), dip the bed lower so the musical drop hits with maximum punch!
        is_high_energy = sec.energy_level > 0.80 or "Chorus" in sec.name or "Drop" in sec.name or "Climax" in sec.name
        if is_classic_vocal:
            # Classic vocal fusion from db0ee3d: words and speech remain prominent, clear and fun in the bed
            base_bed = 0.45 if not is_high_energy else 0.55
        elif pref != "none":
            base_bed = 0.030 if is_high_energy else 0.050
        else:
            base_bed = 0.10 if is_high_energy else 0.15

        target_gain = base_bed * _bed_gain_mul
        if s_end > s_start:
            bed_gain_curve[s_start:s_end] = target_gain
            if i > 0 and s_start > 0:
                prev_base = 0.030 if (arrangement.sections[i - 1].energy_level > 0.80) else 0.050
                prev_gain = prev_base * _bed_gain_mul
                actual_ramp = min(ramp_len, s_end - s_start, s_start)
                if actual_ramp > 1:
                    t_ramp = np.linspace(0.0, np.pi, actual_ramp, dtype=np.float32)
                    w = (0.5 - 0.5 * np.cos(t_ramp)).astype(np.float32)
                    r_start = s_start - actual_ramp // 2
                    r_end = r_start + actual_ramp
                    if 0 <= r_start and r_end <= total_samples:
                        bed_gain_curve[r_start:r_end] = prev_gain * (1.0 - w) + target_gain * w

    # Apply tight tempo-synced sidechain pumping on the bed (breathing on 4-on-the-floor kick)
    if pref != "none" and bpm > 60.0:
        beat_samp = int((60.0 / bpm) * sr)
        if beat_samp > 100:
            num_beats = total_samples // beat_samp + 1
            t_b = np.linspace(0, 1, beat_samp, endpoint=False, dtype=np.float32)
            pump_one_beat = np.clip(0.06 + 0.94 * (t_b ** 0.60), 0.0, 1.0)
            pump_curve = np.tile(pump_one_beat, num_beats)[:total_samples]
            bed_gain_curve *= pump_curve

    mix += raw_bed * bed_gain_curve
    del raw_bed

    # --- STEM 2: HARMONIC CHORD PROGRESSION (Resonated across diverse timeline chunks) ---
    if on_progress:
        on_progress(66, f"Resonating {len(chords)}-chord harmonic progression across timeline ({scale.name})...")
    chord_buffers = []
    num_chords = len(chords)
    bar_samp = int(arrangement.seconds_per_bar * sr)
    chord_src_len = min(len(prep.mono), bar_samp)

    # Distribute chunk offsets across 0% to 100% of the input recording
    offsets = np.linspace(0, max(0, len(prep.mono) - chord_src_len), max(1, num_chords), dtype=int)
    for idx, ch in enumerate(chords):
        off = int(offsets[idx % len(offsets)])
        src_chunk = prep.mono[off:off + chord_src_len].copy()
        if len(src_chunk) < chord_src_len:
            reps = int(np.ceil(chord_src_len / max(1, len(src_chunk))))
            src_chunk = np.tile(src_chunk, reps)[:chord_src_len]

        # De-click and RMS-level the excitation source
        src_chunk = apply_slice_envelope(src_chunk, attack_ms=6.0, release_ms=14.0, sr=sr)
        src_chunk = normalize_slice_rms(src_chunk, target_rms=0.14)

        ch_base = resonant_filter_bank(
            src_chunk,
            frequencies=ch.frequencies,
            q=_chord_q,
            sr=sr,
            envelope_shaping=True
        )
        # Ensure consistent chord volume across distinct source chunks
        ch_base = normalize_slice_rms(ch_base, target_rms=0.18)
        chord_buffers.append(ch_base)

    track_chords = np.zeros((2, total_samples), dtype=np.float32)
    sec_bar_offset = 0
    fade_samples = min(int(0.06 * sr), bar_samp // 4)
    fade_in = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
    fade_out = np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)

    for sec in arrangement.sections:
        if "chords" in sec.active_layers:
            for b in range(sec.bars):
                global_bar = sec_bar_offset + b
                chord_idx = global_bar % len(chords)
                b_start = int((sec.start_time + b * arrangement.seconds_per_bar) * sr)
                b_end = min(total_samples, b_start + bar_samp)
                b_len = b_end - b_start
                raw_c = chord_buffers[chord_idx]
                if len(raw_c) < b_len:
                    fade_seam = min(int(0.02 * sr), len(raw_c) // 4)
                    if fade_seam > 1:
                        raw_c_win = raw_c.copy()
                        w = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fade_seam, dtype=np.float32))
                        raw_c_win[:fade_seam] *= w
                        raw_c_win[-fade_seam:] *= w[::-1]
                    else:
                        raw_c_win = raw_c
                    reps = int(np.ceil(b_len / max(1, len(raw_c_win))))
                    c_chunk = np.tile(raw_c_win, reps)[:b_len].copy()
                else:
                    c_chunk = raw_c[:b_len].copy()

                if fade_samples > 1 and b_len >= fade_samples * 2:
                    c_chunk[:fade_samples] *= fade_in
                    c_chunk[-fade_samples:] *= fade_out

                # --- Artist Archetype Chord Rhythm Engine ---
                step_16 = b_len / 16.0
                chord_env = np.ones(b_len, dtype=np.float32)
                groove = getattr(artist_profile, 'groove_type', '')
                a_id = getattr(artist_profile, 'id', '')

                if groove == "disco_boots_cats" or "disco" in a_id:
                    # Nu-Disco / Dua Lipa: 8th-note upbeat stabs (hits on beats 2, 6, 10, 14)
                    chord_env.fill(0.08)
                    for s in [2, 6, 10, 14]:
                        s_pos = int(s * step_16)
                        hit_len = min(int(step_16 * 1.5), b_len - s_pos)
                        if hit_len > 1:
                            decay_h = np.exp(-np.linspace(0, 3.8, hit_len, dtype=np.float32))
                            chord_env[s_pos:s_pos + hit_len] = np.maximum(chord_env[s_pos:s_pos + hit_len], decay_h)

                elif groove == "synthwave_driving" or "synthwave" in a_id:
                    # 80s Synthwave / The Weeknd: driving 8th-note pulsing arpeggio gate
                    t_b = np.linspace(0, 8.0 * np.pi, b_len, endpoint=False, dtype=np.float32)
                    chord_env = (0.35 + 0.65 * (0.5 + 0.5 * np.sin(t_b))).astype(np.float32)

                elif groove == "pop_four_floor" or "electro" in a_id or a_id == "ladygaga_redone_electro":
                    # Electro-Pop / Lady Gaga: 16th-note driving sidechain pumping stabs
                    chord_env.fill(0.12)
                    for s in range(16):
                        s_pos = int(s * step_16)
                        hit_len = min(int(step_16 * 0.85), b_len - s_pos)
                        if hit_len > 1:
                            decay_h = np.exp(-np.linspace(0, 4.2, hit_len, dtype=np.float32))
                            chord_env[s_pos:s_pos + hit_len] = np.maximum(chord_env[s_pos:s_pos + hit_len], decay_h)

                elif groove == "live_funk_swung" or "funk" in a_id:
                    # Funk / Bruno Mars: Syncopated rhythmic stabs (steps 0, 3, 6, 10, 14)
                    chord_env.fill(0.06)
                    for s in [0, 3, 6, 10, 14]:
                        s_pos = int(s * step_16)
                        hit_len = min(int(step_16 * 1.4), b_len - s_pos)
                        if hit_len > 1:
                            decay_h = np.exp(-np.linspace(0, 3.2, hit_len, dtype=np.float32))
                            chord_env[s_pos:s_pos + hit_len] = np.maximum(chord_env[s_pos:s_pos + hit_len], decay_h)

                elif "trap" in groove or "drill" in groove:
                    # Dark Trap / Metro Boomin: Sparse dramatic minor piano stab on step 0
                    decay_trap = np.exp(-np.linspace(0, 1.8, b_len, dtype=np.float32))
                    chord_env = 0.15 + 0.85 * decay_trap

                c_chunk *= chord_env

                pan_c = rng.uniform(-0.25, 0.25)
                panned_c = apply_panning(c_chunk * (0.78 * sec.energy_level), pan=pan_c)
                track_chords[:, b_start:b_end] += panned_c
        sec_bar_offset += sec.bars
    del chord_buffers

    # Blend with granular pad cloud for depth
    if shared_pad is not None:
        if shared_pad.shape[1] >= total_samples:
            pad_stereo = shared_pad[:, :total_samples]
        else:
            reps = int(np.ceil(total_samples / max(1, shared_pad.shape[1])))
            pad_stereo = np.tile(shared_pad, (1, reps))[:, :total_samples]
    else:
        pad_stereo = create_granular_pad(
            prep.mono,
            target_duration=total_duration,
            semitone_shift=0.0,
            grain_duration=0.16,
            density=8.0,
            sr=sr,
            stereo_spread=True
        )

    for sec in arrangement.sections:
        if "chords" in sec.active_layers:
            s_start = int(sec.start_time * sr)
            s_end = min(total_samples, int((sec.start_time + sec.duration) * sr))
            if s_end > s_start:
                pad_gain = (0.14 * sec.energy_level) if pref != "none" else (0.45 * sec.energy_level)
                sec_pad = pad_stereo[:, s_start:s_end] * pad_gain
                sec_pad = apply_fade(sec_pad, fade_samples=min(int(0.04 * sr), (s_end - s_start) // 4))
                track_chords[:, s_start:s_end] += sec_pad
    del pad_stereo

    _c_room, _c_wet = _chord_reverb
    track_chords = schroeder_reverb(track_chords, room_size=_c_room, wet_level=_c_wet, sr=sr)

    # Daft Punk French Touch resonant filter sweep across chords in Rap mode
    if pref in ["rap", "trap", "drill"]:
        t_arr = np.linspace(0, total_duration, total_samples, endpoint=False, dtype=np.float32)
        sweep_lfo = 0.5 + 0.5 * np.sin(2.0 * np.pi * t_arr / max(2.0, arrangement.seconds_per_bar * 2))
        b_dp, a_dp = signal.butter(1, min(0.45, 2600.0 / (sr * 0.5)), btype='low')
        track_chords[0] = signal.lfilter(b_dp, a_dp, track_chords[0])
        track_chords[1] = signal.lfilter(b_dp, a_dp, track_chords[1])
        track_chords *= (0.72 + 0.38 * sweep_lfo)

    mix += track_chords * _chord_mix
    del track_chords

    # --- STEM 3: PUNCHY DRUMS & PERCUSSION (Full-Timeline Shuffled Selection) ---
    if on_progress:
        on_progress(74, f"Forging punchy noise kick, snare, open hats & groove ({scale.name})...")
    kick_times: List[int] = []

    if beat_preference != "none":
        track_drums = np.zeros((2, total_samples), dtype=np.float32)

        # Build varied genre-tailored one-shot pools (or specialized beatbox mouth drums)
        is_beatbox = bool(smart_profile and getattr(smart_profile, 'has_beatbox', False))
        if is_beatbox and getattr(palette, 'beatbox_kicks', None):
            kick_samples = [render_noise_kick(sl.audio, velocity=0.98, sr=sr, genre=pref) for sl in palette.beatbox_kicks[:4]]
        else:
            kick_samples = [render_noise_kick(sl.audio, velocity=0.96, sr=sr, genre=pref) for sl in palette.impacts[:4]]

        if is_beatbox and getattr(palette, 'beatbox_snares', None):
            snare_samples = [render_noise_snare(sl.audio, velocity=0.92, sr=sr, genre=pref) for sl in palette.beatbox_snares[:4]]
        else:
            snare_sources = (palette.impacts[:3] + palette.movements[:2]) or palette.all_slices[:3]
            snare_samples = [render_noise_snare(sl.audio, velocity=0.90, sr=sr, genre=pref) for sl in snare_sources]

        if is_beatbox and getattr(palette, 'beatbox_hats', None):
            hihat_samples = [render_noise_hihat(sl.audio, velocity=0.76, sr=sr, genre=pref) for sl in palette.beatbox_hats[:5]]
        else:
            hihat_samples = [render_noise_hihat(sl.audio, velocity=0.74, sr=sr, genre=pref) for sl in (palette.pulses[:5] or palette.all_slices[:5])]
        open_hihat_samples = [render_noise_open_hihat(sl.audio, velocity=0.78, sr=sr, genre=pref) for sl in (palette.pulses[:4] or palette.all_slices[:4])]

        kick_bag = BagSelector(kick_samples, rng=rng)
        snare_bag = BagSelector(snare_samples, rng=rng)
        hihat_bag = BagSelector(hihat_samples, rng=rng)
        open_hihat_bag = BagSelector(open_hihat_samples, rng=rng)
        foley_sources = [s for s in (palette.impacts + palette.textures) if getattr(s, "role", "") not in ("VOCAL_PHRASE", "VOCAL_CHOP")] if is_lead_vocal_mode else (palette.impacts + palette.textures)
        foley_bag = BagSelector(foley_sources if foley_sources else (palette.impacts or palette.all_slices), rng=rng)

        sec_bar_offset = 0
        step_dur = arrangement.seconds_per_bar / 16.0

        for sec in arrangement.sections:
            if "drums" in sec.active_layers:
                for b in range(sec.bars):
                    global_bar = sec_bar_offset + b
                    pat_bar = global_bar % 4
                    bar_start_s = int((sec.start_time + b * arrangement.seconds_per_bar) * sr)

                    for step in range(16):
                        step_idx = pat_bar * 16 + step
                        step_s = bar_start_s + int(step * step_dur * sr)
                        if getattr(rhythm_track, 'humanize_timing_ms', 0.0) > 0.0:
                            j_ms = rhythm_track.humanize_timing_ms
                            j_samp = int(rng.uniform(-j_ms, j_ms) * 0.001 * sr)
                            step_s = max(0, min(total_samples - 1, step_s + j_samp))
                        if step_s >= total_samples:
                            continue

                        # 1. Kick Drum
                        k_vel = rhythm_track.kick_pattern[step_idx]
                        if k_vel > 0:
                            base_kick = kick_bag.next()
                            if base_kick is not None:
                                kl = min(len(base_kick), total_samples - step_s)
                                kick_hit = apply_fade(base_kick[:kl], fade_samples=32) * (k_vel * sec.energy_level)
                                track_drums[0, step_s:step_s + kl] += kick_hit
                                track_drums[1, step_s:step_s + kl] += kick_hit
                                kick_times.append(step_s)

                        # 2. Snare / Clap
                        s_vel = rhythm_track.snare_pattern[step_idx]
                        if s_vel > 0:
                            base_snare = snare_bag.next()
                            if base_snare is not None:
                                sl = min(len(base_snare), total_samples - step_s)
                                snare_hit = apply_fade(base_snare[:sl], fade_samples=32) * (s_vel * sec.energy_level)
                                track_drums[0, step_s:step_s + sl] += snare_hit
                                track_drums[1, step_s:step_s + sl] += snare_hit

                        # 3. Closed Hi-Hat
                        h_vel = rhythm_track.hihat_pattern[step_idx]
                        if h_vel > 0:
                            base_hihat = hihat_bag.next()
                            if base_hihat is not None:
                                hl = min(len(base_hihat), total_samples - step_s)
                                hihat_hit = apply_fade(base_hihat[:hl], fade_samples=24) * (h_vel * sec.energy_level)
                                pan_h = rng.uniform(-0.25, 0.25)
                                panned_h = apply_panning(hihat_hit, pan=pan_h)
                                track_drums[:, step_s:step_s + hl] += panned_h

                        # 4. Open Hi-Hat
                        if getattr(rhythm_track, 'open_hihat_pattern', None) is not None:
                            oh_vel = rhythm_track.open_hihat_pattern[step_idx]
                            if oh_vel > 0:
                                base_open_hihat = open_hihat_bag.next()
                                if base_open_hihat is not None:
                                    ohl = min(len(base_open_hihat), total_samples - step_s)
                                    open_hit = apply_fade(base_open_hihat[:ohl], fade_samples=32) * (oh_vel * sec.energy_level)
                                    pan_oh = rng.uniform(0.15, 0.35)
                                    panned_oh = apply_panning(open_hit, pan=pan_oh)
                                    track_drums[:, step_s:step_s + ohl] += panned_oh

                        # 5. Source Foley Percussion Chops
                        sp_vel = rhythm_track.source_perc_pattern[step_idx]
                        if sp_vel > 0:
                            foley_sl = foley_bag.next()
                            if foley_sl is not None:
                                fl = min(len(foley_sl.audio), total_samples - step_s, int(0.18 * sr))
                                if fl > 0:
                                    f_audio = apply_slice_envelope(foley_sl.audio[:fl], attack_ms=2.0, release_ms=6.0, sr=sr)
                                    f_audio = apply_fade(f_audio, fade_samples=24)
                                    pan_f = rng.uniform(-0.45, 0.45)
                                    panned_f = apply_panning(f_audio * sp_vel * 0.70, pan=pan_f)
                                    track_drums[:, step_s:step_s + fl] += panned_f

            sec_bar_offset += sec.bars

        # Sidechain Ducking: Smooth continuous duck curve on each kick hit (zero crackle/click)
        duck_len = int(0.12 * sr)
        attack_len = max(16, int(0.008 * sr))
        release_len = max(32, duck_len - attack_len)
        t_att = np.linspace(0, np.pi, attack_len, endpoint=False)
        duck_attack = 1.0 - 0.30 * 0.5 * (1.0 - np.cos(t_att))
        t_rel = np.linspace(0, 1.0, release_len)
        duck_release = 0.70 + 0.30 * (1.0 - np.exp(-4.0 * t_rel)) / (1.0 - np.exp(-4.0))
        duck_curve = np.concatenate([duck_attack, duck_release]).astype(np.float32)

        for ks in kick_times:
            d_end = min(total_samples, ks + duck_len)
            dl = d_end - ks
            if dl > 0:
                mix[:, ks:d_end] *= duck_curve[:dl]

        mix += track_drums * 0.95
        del track_drums

    # --- STEM 4: DEEP GROOVING SUB-BASS (Fused with Timeline Low-End Movements) ---
    if on_progress:
        on_progress(82, "Carving deep analog-saturated 808 sub-bass...")
    track_bass = np.zeros((2, total_samples), dtype=np.float32)
    b_lp, a_lp = signal.butter(2, min(0.45, 320.0 / (sr * 0.5)), btype='low')
    prefiltered_bass_source = signal.lfilter(b_lp, a_lp, prep.mono)
    p_src = np.max(np.abs(prefiltered_bass_source))
    if p_src > 1e-4:
        prefiltered_bass_source = prefiltered_bass_source / p_src

    bass_slices = (palette.drones + palette.tonal + palette.impacts) or palette.all_slices
    bass_slice_bag = BagSelector(bass_slices, rng=rng)
    sec_bar_offset = 0
    if _bass_style == "808_glide":
        # Saturated Pitch-Gliding 808 Sub-Bass (Metro Boomin, Usher Crunk, Atlanta Trap, Reggaeton)
        step_8_sec = arrangement.seconds_per_bar / 8.0
        note_dur = step_8_sec * 1.85

        for sec in arrangement.sections:
            if "bass" in sec.active_layers:
                for b in range(sec.bars):
                    global_bar = sec_bar_offset + b
                    chord_idx = global_bar % len(chords)
                    chord = chords[chord_idx]
                    bar_time = sec.start_time + b * arrangement.seconds_per_bar
                    root_f = midi_to_hz(chord.root_midi)
                    oct_f = midi_to_hz(chord.root_midi + 12)
                    fifth_f = midi_to_hz(chord.root_midi + 7)

                    trap_steps = [
                        (0, root_f * (1.5 if getattr(artist_profile, "id", "") == "usher_liljon_crunk" else 1.0), root_f, 0.98),
                        (3, root_f, fifth_f, 0.88),
                        (6, root_f, oct_f, 0.95)
                    ]
                    for s8, f_st, f_nd, vel_b in trap_steps:
                        s_start = int((bar_time + s8 * step_8_sec) * sr)
                        if s_start >= total_samples:
                            continue

                        b_sl = bass_slice_bag.next()
                        b_audio = b_sl.audio if b_sl is not None else None
                        rendered_bass = render_trap_808_glide_bass(
                            source_audio=prefiltered_bass_source,
                            freq_start=f_st,
                            freq_end=f_nd,
                            duration=note_dur,
                            velocity=vel_b * sec.energy_level,
                            sr=sr,
                            glide_sec=0.045 if getattr(artist_profile, "id", "") == "usher_liljon_crunk" else 0.075,
                            slice_audio=b_audio
                        )
                        bl = min(len(rendered_bass), total_samples - s_start)
                        if bl > 0:
                            b_hit = apply_fade(rendered_bass[:bl], fade_samples=48)
                            track_bass[0, s_start:s_start + bl] += b_hit
                            track_bass[1, s_start:s_start + bl] += b_hit
            sec_bar_offset += sec.bars

    elif _bass_style == "disco_octave_pump":
        # Dua Lipa Nu-Disco: 16th-note driving octave pump bassline (Don't Start Now / Studio 54)
        step_16_sec = arrangement.seconds_per_bar / 16.0
        note_dur = step_16_sec * 0.88

        for sec in arrangement.sections:
            if "bass" in sec.active_layers:
                for b in range(sec.bars):
                    global_bar = sec_bar_offset + b
                    chord_idx = global_bar % len(chords)
                    chord = chords[chord_idx]
                    bar_time = sec.start_time + b * arrangement.seconds_per_bar
                    root_f = midi_to_hz(chord.root_midi)
                    while root_f > 115.0:
                        root_f /= 2.0
                    while root_f < 40.0:
                        root_f *= 2.0
                    oct_f = root_f * 2.0
                    fifth_f = root_f * 1.5

                    # Hypnotic 16th driving disco octave bounce
                    disco_hits = [
                        (0, root_f, 0.98), (1, oct_f, 0.78), (2, oct_f, 0.88), (3, root_f, 0.82),
                        (4, root_f, 0.98), (5, oct_f, 0.78), (6, oct_f, 0.88), (7, fifth_f, 0.84),
                        (8, root_f, 0.98), (9, oct_f, 0.80), (10, oct_f, 0.90), (11, root_f, 0.82),
                        (12, root_f, 0.98), (13, oct_f, 0.80), (14, oct_f, 0.92), (15, oct_f, 0.85)
                    ]
                    for s16, f_n, vel_b in disco_hits:
                        s_start = int((bar_time + s16 * step_16_sec) * sr)
                        if s_start >= total_samples:
                            continue
                        b_sl = bass_slice_bag.next()
                        b_audio = b_sl.audio if b_sl is not None else None
                        rendered_bass = render_noise_bass_note(
                            source_audio=prefiltered_bass_source,
                            freq=f_n,
                            duration=note_dur,
                            velocity=vel_b * sec.energy_level,
                            sr=sr,
                            is_prefiltered=True,
                            slice_audio=b_audio
                        )
                        bl = min(len(rendered_bass), total_samples - s_start)
                        if bl > 0:
                            b_hit = apply_fade(rendered_bass[:bl], fade_samples=32)
                            track_bass[0, s_start:s_start + bl] += b_hit
                            track_bass[1, s_start:s_start + bl] += b_hit
            sec_bar_offset += sec.bars

    elif _bass_style == "billie_jean_ostinato":
        # Michael Jackson & Quincy Jones: Driving 8th-note walking synth ostinato ("Billie Jean" / "Thriller")
        # Step: 0 (Root), 2 (5th below), 4 (b7 below), 6 (Root), 8 (b7 below), 10 (5th below), 12 (4th below), 14 (5th below)
        step_16_sec = arrangement.seconds_per_bar / 16.0
        note_dur = step_16_sec * 1.35  # Snappy staccato 8th notes

        for sec in arrangement.sections:
            if "bass" in sec.active_layers:
                for b in range(sec.bars):
                    global_bar = sec_bar_offset + b
                    chord_idx = global_bar % len(chords)
                    chord = chords[chord_idx]
                    bar_time = sec.start_time + b * arrangement.seconds_per_bar
                    root_f = midi_to_hz(chord.root_midi)
                    while root_f > 110.0:
                        root_f /= 2.0
                    while root_f < 44.0:
                        root_f *= 2.0

                    f_r = root_f
                    f_5th_down = root_f * (2.0 ** (-7.0 / 12.0))
                    f_b7_down = root_f * (2.0 ** (-2.0 / 12.0))
                    f_4th_down = root_f * (2.0 ** (-5.0 / 12.0))

                    ostinato_hits = [
                        (0, f_r, 1.00),
                        (2, f_5th_down, 0.88),
                        (4, f_b7_down, 0.92),
                        (6, f_r, 0.96),
                        (8, f_b7_down, 0.90),
                        (10, f_5th_down, 0.86),
                        (12, f_4th_down, 0.88),
                        (14, f_5th_down, 0.86),
                    ]
                    for s16, f_n, vel_b in ostinato_hits:
                        s_start = int((bar_time + s16 * step_16_sec) * sr)
                        if s_start >= total_samples:
                            continue
                        b_sl = bass_slice_bag.next()
                        b_audio = b_sl.audio if b_sl is not None else None
                        rendered_bass = render_noise_bass_note(
                            source_audio=prefiltered_bass_source,
                            freq=f_n,
                            duration=note_dur,
                            velocity=vel_b * sec.energy_level,
                            sr=sr,
                            is_prefiltered=True,
                            slice_audio=b_audio
                        )
                        bl = min(len(rendered_bass), total_samples - s_start)
                        if bl > 0:
                            b_hit = apply_fade(rendered_bass[:bl], fade_samples=32)
                            track_bass[0, s_start:s_start + bl] += b_hit
                            track_bass[1, s_start:s_start + bl] += b_hit
            sec_bar_offset += sec.bars

    elif _bass_style in ["karplus_bass", "karplus_slap"]:
        # Karplus-Strong physical modeling bass guitar / funk slap bass (Michael Jackson, Bruno Mars, J Dilla)
        step_16_sec = arrangement.seconds_per_bar / 16.0
        note_dur = step_16_sec * 1.6
        is_slap = (_bass_style == "karplus_slap")
        damp = 0.992 if is_slap else 0.996

        for sec in arrangement.sections:
            if "bass" in sec.active_layers:
                for b in range(sec.bars):
                    global_bar = sec_bar_offset + b
                    chord_idx = global_bar % len(chords)
                    chord = chords[chord_idx]
                    bar_time = sec.start_time + b * arrangement.seconds_per_bar
                    root_f = midi_to_hz(chord.root_midi)
                    while root_f > 115.0:
                        root_f /= 2.0
                    while root_f < 38.0:
                        root_f *= 2.0
                    oct_f = root_f * 2.0
                    fifth_f = root_f * 1.5

                    funk_hits = [
                        (0, root_f, 0.98),
                        (3, fifth_f, 0.84),
                        (6, oct_f, 0.92),
                        (8, root_f, 0.94),
                        (11, root_f, 0.78),
                        (14, oct_f, 0.96)
                    ]
                    for s16, f_n, vel_b in funk_hits:
                        s_start = int((bar_time + s16 * step_16_sec) * sr)

                        if s_start >= total_samples:
                            continue
                        b_sl = bass_slice_bag.next()
                        b_grain = b_sl.audio if (b_sl is not None and len(b_sl.audio) > 0) else prefiltered_bass_source[:int(0.08 * sr)]
                        rendered_bass = render_karplus_strong_noise_note(
                            source_grain=b_grain,
                            freq=f_n,
                            duration=note_dur,
                            velocity=vel_b * sec.energy_level,
                            damping=damp,
                            brightness=0.62 if is_slap else 0.50,
                            sr=sr,
                            is_slap=is_slap
                        )
                        bl = min(len(rendered_bass), total_samples - s_start)
                        if bl > 0:
                            b_hit = apply_fade(rendered_bass[:bl], fade_samples=48)
                            track_bass[0, s_start:s_start + bl] += b_hit
                            track_bass[1, s_start:s_start + bl] += b_hit
            sec_bar_offset += sec.bars

    elif _bass_style == "saw_pluck":
        # Lady Gaga / RedOne: Sawtooth sub pluck synced to kick, short decay, no glide
        step_16_sec = arrangement.seconds_per_bar / 16.0
        note_dur = step_16_sec * 0.85

        for sec in arrangement.sections:
            if "bass" in sec.active_layers:
                for b in range(sec.bars):
                    global_bar = sec_bar_offset + b
                    chord_idx = global_bar % len(chords)
                    chord = chords[chord_idx]
                    bar_time = sec.start_time + b * arrangement.seconds_per_bar
                    root_f = midi_to_hz(chord.root_midi)
                    oct_f = midi_to_hz(chord.root_midi + 12)

                    for s16 in range(16):
                        if s16 in [0, 4, 8, 12]:
                            f_note = root_f
                            vel_b = 0.98 * sec.energy_level
                        elif s16 in [2, 6, 10, 14]:
                            f_note = oct_f
                            vel_b = 0.86 * sec.energy_level
                        else:
                            continue

                        s_start = int((bar_time + s16 * step_16_sec) * sr)
                        if s_start >= total_samples:
                            continue

                        b_sl = bass_slice_bag.next()
                        b_audio = b_sl.audio if b_sl is not None else None
                        rendered_bass = render_noise_bass_note(
                            source_audio=prefiltered_bass_source,
                            freq=f_note,
                            duration=note_dur,
                            velocity=vel_b,
                            sr=sr,
                            is_prefiltered=True,
                            slice_audio=b_audio
                        )
                        bl = min(len(rendered_bass), total_samples - s_start)
                        if bl > 0:
                            b_hit = apply_fade(rendered_bass[:bl], fade_samples=48)
                            track_bass[0, s_start:s_start + bl] += b_hit
                            track_bass[1, s_start:s_start + bl] += b_hit
            sec_bar_offset += sec.bars

    elif _bass_style == "sub_octave_pulse":
        # The Weeknd / Max Martin: Sub-octave pulse doubling root motion, driving 8ths, tight and punchy
        step_8_sec = arrangement.seconds_per_bar / 8.0
        note_dur = step_8_sec * 0.88

        for sec in arrangement.sections:
            if "bass" in sec.active_layers:
                for b in range(sec.bars):
                    global_bar = sec_bar_offset + b
                    chord_idx = global_bar % len(chords)
                    chord = chords[chord_idx]
                    bar_time = sec.start_time + b * arrangement.seconds_per_bar
                    root_f = midi_to_hz(chord.root_midi)

                    for s8 in range(8):
                        s_start = int((bar_time + s8 * step_8_sec) * sr)
                        if s_start >= total_samples:
                            continue
                        b_sl = bass_slice_bag.next()
                        b_audio = b_sl.audio if b_sl is not None else None
                        rendered_bass = render_noise_bass_note(
                            source_audio=prefiltered_bass_source,
                            freq=root_f,
                            duration=note_dur,
                            velocity=0.94 * sec.energy_level,
                            sr=sr,
                            is_prefiltered=True,
                            slice_audio=b_audio
                        )
                        bl = min(len(rendered_bass), total_samples - s_start)
                        if bl > 0:
                            b_hit = apply_fade(rendered_bass[:bl], fade_samples=48)
                            track_bass[0, s_start:s_start + bl] += b_hit
                            track_bass[1, s_start:s_start + bl] += b_hit
            sec_bar_offset += sec.bars

    elif _bass_style == "horn_punctuation":
        # Dr. Dre / Scott Storch: Sparse horn-synth bass punctuation, short percussive envelope
        step_8_sec = arrangement.seconds_per_bar / 8.0
        note_dur = 0.38

        for sec in arrangement.sections:
            if "bass" in sec.active_layers:
                for b in range(sec.bars):
                    global_bar = sec_bar_offset + b
                    chord_idx = global_bar % len(chords)
                    chord = chords[chord_idx]
                    bar_time = sec.start_time + b * arrangement.seconds_per_bar
                    root_f = midi_to_hz(chord.root_midi)

                    for s8, vel_b in [(0, 0.98), (6, 0.88)]:
                        s_start = int((bar_time + s8 * step_8_sec) * sr)
                        if s_start >= total_samples:
                            continue
                        b_sl = bass_slice_bag.next()
                        b_audio = b_sl.audio if b_sl is not None else None
                        rendered_bass = render_noise_bass_note(
                            source_audio=prefiltered_bass_source,
                            freq=root_f,
                            duration=note_dur,
                            velocity=vel_b * sec.energy_level,
                            sr=sr,
                            is_prefiltered=True,
                            slice_audio=b_audio
                        )
                        bl = min(len(rendered_bass), total_samples - s_start)
                        if bl > 0:
                            b_hit = apply_fade(rendered_bass[:bl], fade_samples=48)
            sec_bar_offset += sec.bars

    elif _bass_style in ["saw_pluck", "electro_saw_pluck"]:
        # Lady Gaga / RedOne Electro: 16th-note saturated saw bass pluck on driving steps [0, 3, 6, 8, 11, 14]
        step_16_sec = arrangement.seconds_per_bar / 16.0
        note_dur = step_16_sec * 0.90
        for sec in arrangement.sections:
            if "bass" in sec.active_layers:
                for b in range(sec.bars):
                    global_bar = sec_bar_offset + b
                    chord_idx = global_bar % len(chords)
                    chord = chords[chord_idx]
                    bar_time = sec.start_time + b * arrangement.seconds_per_bar
                    root_f = midi_to_hz(chord.root_midi)
                    while root_f > 110.0:
                        root_f /= 2.0
                    oct_f = root_f * 2.0

                    saw_hits = [(0, root_f, 1.0), (3, root_f, 0.85), (6, oct_f, 0.95), (8, root_f, 1.0), (11, oct_f, 0.90), (14, root_f, 0.92)]
                    for s16, f_n, vel_b in saw_hits:
                        s_start = int((bar_time + s16 * step_16_sec) * sr)
                        if s_start >= total_samples:
                            continue
                        b_sl = bass_slice_bag.next()
                        b_audio = b_sl.audio if b_sl is not None else None
                        rendered_bass = render_noise_bass_note(
                            source_audio=prefiltered_bass_source,
                            freq=f_n,
                            duration=note_dur,
                            velocity=vel_b * sec.energy_level,
                            sr=sr,
                            is_prefiltered=True,
                            slice_audio=b_audio
                        )
                        bl = min(len(rendered_bass), total_samples - s_start)
                        if bl > 0:
                            b_hit = apply_fade(rendered_bass[:bl], fade_samples=24)
                            track_bass[0, s_start:s_start + bl] += b_hit
                            track_bass[1, s_start:s_start + bl] += b_hit
            sec_bar_offset += sec.bars

    else:
        # Standard warm sub-bass or ambient sustained sub
        step_8_sec = arrangement.seconds_per_bar / 8.0
        for sec in arrangement.sections:
            if "bass" in sec.active_layers:
                for b in range(sec.bars):
                    global_bar = sec_bar_offset + b
                    chord_idx = global_bar % len(chords)
                    chord = chords[chord_idx]
                    bar_time = sec.start_time + b * arrangement.seconds_per_bar
                    root_f = midi_to_hz(chord.root_midi)
                    fifth_f = midi_to_hz(chord.root_midi + 7)

                    hits = [(0.0, root_f, 0.94)]
                    if _bass_style != "sub_drone":
                        hits.append((arrangement.seconds_per_bar * 0.5, fifth_f, 0.88))

                    b_dur = arrangement.seconds_per_bar * (0.92 if _bass_style == "sub_drone" else 0.45)
                    for b_sec, f_note, vel_b in hits:
                        b_start = int((bar_time + b_sec) * sr)
                        if b_start >= total_samples:
                            continue
                        b_sl = bass_slice_bag.next()
                        b_audio = b_sl.audio if b_sl is not None else None
                        rendered_bass = render_noise_bass_note(
                            source_audio=prefiltered_bass_source,
                            freq=f_note,
                            duration=b_dur,
                            velocity=vel_b * sec.energy_level,
                            sr=sr,
                            is_prefiltered=True,
                            slice_audio=b_audio
                        )
                        bl = min(len(rendered_bass), total_samples - b_start)
                        if bl > 0:
                            b_hit = apply_fade(rendered_bass[:bl], fade_samples=48)
                            track_bass[0, b_start:b_start + bl] += b_hit
                            track_bass[1, b_start:b_start + bl] += b_hit
            sec_bar_offset += sec.bars

    del prefiltered_bass_source

    # Clean Sidechain Ducking on Bass:
    # Smoothly dip sub-bass on every kick impact so kick and sub-bass never clash or clip
    if len(kick_times) > 0:
        duck_len_b = int(0.12 * sr)
        attack_len_b = max(16, int(0.008 * sr))
        release_len_b = max(32, duck_len_b - attack_len_b)
        t_att_b = np.linspace(0, np.pi, attack_len_b, endpoint=False)
        duck_att_b = 1.0 - 0.40 * 0.5 * (1.0 - np.cos(t_att_b))
        t_rel_b = np.linspace(0, 1.0, release_len_b)
        duck_rel_b = 0.60 + 0.40 * (1.0 - np.exp(-4.5 * t_rel_b)) / (1.0 - np.exp(-4.5))
        duck_curve_bass = np.concatenate([duck_att_b, duck_rel_b]).astype(np.float32)

        for ks in kick_times:
            d_end = min(total_samples, ks + duck_len_b)
            dl = d_end - ks
            if dl > 0:
                track_bass[:, ks:d_end] *= duck_curve_bass[:dl]

    bass_drive = 1.15
    if pref in ["trap", "drill"]:
        bass_drive = 1.50
    elif pref in ["rap", "electro"]:
        bass_drive = 1.35
    elif pref in ["hiphop", "hip_hop", "lofi"]:
        bass_drive = 1.22
    elif pref in ["pop", "dance"]:
        bass_drive = 1.20
    elif pref in ["pop", "dance"]:
        bass_drive = 1.22
    track_bass = soft_saturation(track_bass, drive=bass_drive)
    mix += track_bass * _bass_mix
    del track_bass

    # --- STEM 5: CATCHY MELODIC LEAD / HOOK (Rotated Grains across Full Timeline) ---
    track_melody = np.zeros((2, total_samples), dtype=np.float32)
    lead_style = _lead_style
    if on_progress:
        on_progress(88, f"Synthesizing tuned melodic hook ({lead_style.title()}) & ping-pong delay...")

    tonal_grains = [s.audio for s in palette.tonal] if palette.tonal else [s.audio for s in (palette.pulses + palette.impacts)]
    melody_grain_bag = BagSelector(tonal_grains, rng=rng)

    for event in melody_events:
        sec = next((s for s in arrangement.sections if s.start_time <= event.start_time < s.start_time + s.duration), None)
        if sec and "melody" in sec.active_layers:
            start_s = int(event.start_time * sr)
            if start_s < total_samples:
                cur_grain = melody_grain_bag.next()
                if cur_grain is None or len(cur_grain) == 0:
                    cur_grain = prep.mono[:min(len(prep.mono), int(0.08 * sr))]

                intro_lead = getattr(artist_profile, 'intro_lead_style', '')
                is_intro_outro = bool(sec and ("Intro" in sec.name or "Outro" in sec.name or "Hook" in sec.name and "Chorus" not in sec.name))
                cur_lead = (intro_lead if (intro_lead and is_intro_outro) else lead_style)

                if is_classic_vocal:
                    # Classic physical voice-resonated hook: excite directly from full source recording across random windows
                    note_audio = render_noise_instrument_note(
                        source_audio=prep.mono,
                        freq=event.freq_hz,
                        duration=event.duration,
                        velocity=event.velocity * sec.energy_level * 0.88,
                        style=cur_lead,
                        sr=sr
                    )
                elif cur_lead == "karplus":
                    note_audio = render_karplus_strong_noise_note(
                        source_grain=cur_grain,
                        freq=event.freq_hz,
                        duration=event.duration,
                        velocity=event.velocity * sec.energy_level * 0.92,
                        damping=0.986,
                        brightness=0.60,
                        sr=sr
                    )
                else:
                    note_audio = render_noise_instrument_note(
                        source_audio=cur_grain,
                        freq=event.freq_hz,
                        duration=event.duration,
                        velocity=event.velocity * sec.energy_level * 0.88,
                        style=cur_lead,
                        sr=sr
                    )
                pan = rng.uniform(-0.35, 0.35)
                panned_note = apply_panning(note_audio, pan=pan)
                nl = min(panned_note.shape[1], total_samples - start_s)
                if nl > 0:
                    track_melody[:, start_s:start_s + nl] += apply_fade(panned_note[:, :nl], fade_samples=48)

    _div, _fb, _dmix = _melody_delay
    _m_room, _m_wet = _melody_reverb
    track_melody = ping_pong_delay(track_melody, bpm=bpm, division=_div, feedback=_fb, mix=_dmix, sr=sr)
    track_melody = schroeder_reverb(track_melody, room_size=_m_room, wet_level=_m_wet, sr=sr)
    mix += track_melody * _melody_mix
    del track_melody

    # --- STEM 5.5: VOCAL LEAD & SCALE-AUTO-TUNED HOOK (Full Phrases or Syllabic Chops) ---
    track_vocal_hook = np.zeros((2, total_samples), dtype=np.float32)
    is_vocal_source = bool(
        smart_profile and (
            getattr(smart_profile, 'has_speech_or_vocal', False)
            or getattr(smart_profile, 'has_humming', False)
            or getattr(smart_profile, 'primary_category', '') == "VOCAL"
        )
    )
    is_hum = bool(smart_profile and getattr(smart_profile, 'has_humming', False))
    available_phrases = getattr(palette, 'full_vocal_phrases', [])
    lead_take = getattr(palette, 'lead_vocal_take', None)

    # Detect genuine singing or humming (avoids turning spoken words into crackly robotic chords)
    _phrase_pitch_confs = [p.pitch_conf for p in available_phrases if getattr(p, "pitch_conf", 0.0) > 0]
    has_strong_singing_pitch = bool(
        getattr(analysis.pitch, "has_reliable_pitch", False)
        and len(_phrase_pitch_confs) > 0
        and float(np.mean(_phrase_pitch_confs)) >= 0.68
    )
    is_singing = bool(is_hum or has_strong_singing_pitch)

    # Determine if Lead Vocal (Full Phrase Take) mode is activated
    # Solves cutoff complaints: full phrase preserves entire sentences, intact words and lyrics
    use_lead_vocal_take = bool(
        is_vocal_source
        and (
            (vocal_mode in ("lead", "full_phrase"))
            or (vocal_mode == "auto" and len(available_phrases) > 0)
        )
        and (len(available_phrases) > 0 or (lead_take is not None and len(lead_take) > int(0.8 * sr)))
    )

    # chops mode is explicitly requested
    force_chops_mode = bool(
        vocal_mode == "chops"
    )

    has_source_horn_stabs = bool(
        not is_vocal_source
        and getattr(palette, 'traffic_horns', None)
        and any(getattr(s, 'pitch_conf', 0.0) > 0.35 or 300.0 <= getattr(s, 'dominant_pitch_hz', 0.0) <= 2200.0 for s in palette.traffic_horns)
    )

    has_vocal_content = bool(
        use_lead_vocal_take
        or (is_vocal_source and vocal_mode in ("lead", "full_phrase", "chops"))
        or (is_vocal_source and bool(getattr(palette, 'vocal_chops', [])))
        or has_source_horn_stabs
    )
    if is_classic_vocal:
        # Voice is already integrated into the pumping bed, melody, and stutters like in db0ee3d!
        has_vocal_content = False

    if has_vocal_content:
        if use_lead_vocal_take and not force_chops_mode:
            if on_progress:
                on_progress(91, f"Arranging Continuous Lead Vocal track: studio vocal chain ({scale.name})...")

            # 1. Obtain entire, unbroken lead vocal take (never chopped or fragmented)
            raw_lead = lead_take if (lead_take is not None and len(lead_take) > 0) else prep.mono
            clean_lead = dehiss_audio(raw_lead, sr=sr, high_cut_hz=14500.0, gate_threshold_db=-46.0)

            # 2. Studio High-Pass Filter (75 Hz) to remove sub rumble, plosives, and handling noise
            try:
                b_hp, a_hp = signal.butter(2, 75.0 / (sr * 0.5), btype='high')
                clean_lead = signal.lfilter(b_hp, a_hp, clean_lead)
            except Exception:
                pass

            # 3. High-shelf presence air boost (4.0 kHz) for crystal-clear lyric diction & air
            try:
                b_air, a_air = signal.butter(1, 4000.0 / (sr * 0.5), btype='high')
                air_boost = signal.lfilter(b_air, a_air, clean_lead) * 0.12
                clean_lead = np.clip(clean_lead + air_boost, -1.0, 1.0)
            except Exception:
                pass

            # 4. Auto-Tuning & Harmonization:
            # Singing / Humming: quantize sustained pitch & stack lush 3rd/5th choir harmonies
            # Speaking / Voice Memos: keep 100% natural, continuous, and clear without robotic crackle or flanging
            if is_singing or is_hum:
                lead_processed = auto_tune_continuous_phrase(
                    clean_lead,
                    scale_midis=scale_midis,
                    sr=sr,
                    strength=0.95,
                    retune_speed=0.85,
                    is_singing=True
                )
                harm_semi = [0.0, 3.0, 7.0] if "minor" in scale.name.lower() else [0.0, 4.0, 7.0]
                harm_weights = [1.0, 0.45, 0.32] if not is_hum else [1.0, 0.60, 0.40]
                lead_processed = harmonize_vocal_slice(lead_processed, intervals=harm_semi, weights=harm_weights, sr=sr)
            else:
                lead_processed = clean_lead.copy()

            lead_processed = normalize_slice_rms(lead_processed, target_rms=0.22)
            lead_len = len(lead_processed)

            # 5. Continuous Timeline Placement:
            # Preserves the full take in continuous chronological sequence without chopping or section scattering
            verse_sec = next((s for s in arrangement.sections if "Verse" in s.name or "Drop" in s.name or "Chorus" in s.name), arrangement.sections[0])

            # If recording is long (fits whole song or near total duration), start right at 0.0s
            if lead_len >= (total_samples - int(2.5 * sr)):
                v_start = 0
            else:
                # Drop vocal on beat 1 of verse after intro
                v_start = int(verse_sec.start_time * sr)

            v_end = min(total_samples, v_start + lead_len)
            v_actual_len = v_end - v_start
            if v_actual_len > 128:
                v_chunk = lead_processed[:v_actual_len].copy()
                fade_v = min(int(0.02 * sr), v_actual_len // 8)
                if fade_v > 2:
                    w_v = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fade_v, dtype=np.float32))
                    v_chunk[:fade_v] *= w_v
                    v_chunk[-fade_v:] *= w_v[::-1]

                track_vocal_hook[0, v_start:v_end] += v_chunk * 1.05
                track_vocal_hook[1, v_start:v_end] += v_chunk * 1.05

            # If vocal is short (< 14s) and ends before song ends, repeat take in Chorus/Drop
            if lead_len < int(14.0 * sr):
                chorus_sec = next((s for s in arrangement.sections if ("Chorus" in s.name or "Climax" in s.name) and (s.start_time * sr) >= v_end), None)
                if chorus_sec:
                    c_start = int(chorus_sec.start_time * sr)
                    c_end = min(total_samples, c_start + lead_len)
                    c_len = c_end - c_start
                    if c_len > 128:
                        c_chunk = lead_processed[:c_len].copy()
                        fade_c = min(int(0.02 * sr), c_len // 8)
                        if fade_c > 2:
                            w_c = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fade_c, dtype=np.float32))
                            c_chunk[:fade_c] *= w_c
                            c_chunk[-fade_c:] *= w_c[::-1]
                        track_vocal_hook[0, c_start:c_end] += c_chunk * 1.08
                        track_vocal_hook[1, c_start:c_end] += c_chunk * 1.08

            # 6. Studio vocal chain: stereo delay + reverb for depth and space
            track_vocal_hook = ping_pong_delay(track_vocal_hook, bpm=bpm, division=0.5, feedback=0.24, mix=0.18, sr=sr)
            track_vocal_hook = schroeder_reverb(track_vocal_hook, room_size=0.40, wet_level=0.20, sr=sr)

            # 7. Dynamic Vocal Sidechain Ducking on Accompaniment:
            # When lead vocal is speaking or singing, smoothly duck chords/pads by -3.5 dB
            v_mono = 0.5 * (np.abs(track_vocal_hook[0]) + np.abs(track_vocal_hook[1]))
            if np.max(v_mono) > 1e-4:
                try:
                    b_env, a_env = signal.butter(1, 10.0 / (sr * 0.5), btype='low')
                    v_smoothed = signal.lfilter(b_env, a_env, v_mono)
                    v_smoothed = v_smoothed / (np.max(v_smoothed) + 1e-6)
                    duck_curve = (1.0 - 0.35 * np.clip(v_smoothed * 2.0, 0.0, 1.0)).astype(np.float32)
                    mix[0] *= duck_curve
                    mix[1] *= duck_curve
                except Exception:
                    pass

            mix += track_vocal_hook * 1.10
            del track_vocal_hook

        else:
            # Syllabic Chops Mode OR Auto-Tuned Traffic Horn Stabs Mode
            if has_source_horn_stabs:
                source_v_slices = [s for s in palette.traffic_horns if (getattr(s, 'pitch_conf', 0.0) > 0.30 or 250.0 <= getattr(s, 'dominant_pitch_hz', 0.0) <= 2400.0)]
                if not source_v_slices:
                    source_v_slices = palette.traffic_horns
            elif is_hum and palette.humming_slices:
                source_v_slices = palette.humming_slices
            else:
                source_v_slices = palette.vocal_chops
            vocal_bag = BagSelector(source_v_slices, rng=rng)

            hook_title = "traffic horn & brass stabs" if has_source_horn_stabs else "vocal hooks & soul chops"
            if on_progress:
                on_progress(91, f"Arranging scale-Auto-Tuned {hook_title} ({scale.name})...")

            step_dur = arrangement.seconds_per_bar / 16.0
            sec_bar_offset = 0
            for sec in arrangement.sections:
                is_hook_section = (
                    "vocal_hook" in sec.active_layers
                    or "Chorus" in sec.name
                    or "Climax" in sec.name
                    or "Drop" in sec.name
                    or "Hook" in sec.name
                    or (sec.energy_level > 0.62)
                )
                if is_hook_section:
                    for b in range(sec.bars):
                        global_bar = sec_bar_offset + b
                        bar_start_s = int((sec.start_time + b * arrangement.seconds_per_bar) * sr)
                        chord_idx = global_bar % len(chords)
                        chord = chords[chord_idx]
                        chord_midis = [int(round(hz_to_midi(f))) for f in chord.frequencies]

                        hook_steps = [4, 10] if (b % 2 == 0) else [6, 12, 14]
                        for h_idx, h_step in enumerate(hook_steps):
                            step_s = bar_start_s + int(h_step * step_dur * sr)
                            if step_s >= total_samples:
                                continue
                            cur_vocal = vocal_bag.next()
                            if cur_vocal is not None and len(cur_vocal.audio) > 0:
                                target_midi_candidates = [chord_midis[h_idx % len(chord_midis)]] if chord_midis else scale_midis
                                tuned_vocal, det_hz, target_note = auto_tune_slice(
                                    cur_vocal.audio,
                                    scale_midis=scale_midis,
                                    target_chord_midis=target_midi_candidates,
                                    strength=1.0,
                                    sr=sr
                                )
                                if is_hum:
                                    harm_semi = [0.0, 3.0, 7.0] if "minor" in scale.name.lower() else [0.0, 4.0, 7.0]
                                    tuned_vocal = harmonize_vocal_slice(tuned_vocal, intervals=harm_semi, weights=[1.0, 0.65, 0.45], sr=sr)

                                pitch_shift_semi = 0.0
                                if det_hz <= 0.0 and chord_midis:
                                    target_midi = chord_midis[h_idx % len(chord_midis)]
                                    pitch_shift_semi = float((target_midi - 60) % 12)
                                    if pitch_shift_semi > 6:
                                        pitch_shift_semi -= 12

                                c_note = render_pitched_vocal_chop(
                                    slice_audio=tuned_vocal,
                                    semitones=pitch_shift_semi,
                                    duration=min(0.42, step_dur * 3.8),
                                    velocity=0.92 * sec.energy_level,
                                    sr=sr
                                )
                                pan_v = rng.uniform(-0.25, 0.25)
                                panned_v = apply_panning(c_note, pan=pan_v)
                                vl = min(panned_v.shape[1], total_samples - step_s)
                                if vl > 0:
                                    track_vocal_hook[:, step_s:step_s + vl] += panned_v[:, :vl]
                sec_bar_offset += sec.bars

            track_vocal_hook = ping_pong_delay(track_vocal_hook, bpm=bpm, division=0.5, feedback=0.30, mix=0.25, sr=sr)
            track_vocal_hook = schroeder_reverb(track_vocal_hook, room_size=0.48, wet_level=0.25, sr=sr)
            mix += track_vocal_hook * (0.88 if is_hum else 0.82)
            del track_vocal_hook


    # --- STEM 6: STRUCTURAL RISERS, DOWNLIFTERS & ACCENTS (Timeline Diversity) ---
    accent_bag = BagSelector(palette.accents if palette.accents else palette.impacts, rng=rng)

    for sec in arrangement.sections:
        # 1. Rising noise sweep leading up to Chorus_Climax
        if "riser" in sec.active_layers:
            riser_dur = min(sec.duration, 3.5)
            r_off = int(len(prep.mono) * 0.5)
            riser_audio = render_noise_riser(prep.mono, duration=riser_dur, sr=sr, offset_sample=r_off)
            r_start = int((sec.start_time + sec.duration - riser_dur) * sr)
            rl = min(len(riser_audio), total_samples - r_start)
            if rl > 0 and r_start >= 0:
                panned_riser = apply_panning(apply_fade(riser_audio[:rl], fade_samples=48) * 0.85, pan=0.0)
                mix[:, r_start:r_start + rl] += panned_riser * 0.65

        # 2. Downlifter / Impact crash / Auto-Tuned Car Horn stab at Chorus_Climax drop
        if sec.name == "Chorus_Climax":
            down_sl = accent_bag.next()
            dl_audio = down_sl.audio if down_sl is not None else palette.impacts[0].audio
            # If traffic horns present, auto-tune the horn stab to the scale root!
            if smart_profile and getattr(smart_profile, 'has_traffic_or_engine', False) and palette.traffic_horns:
                horn_raw = palette.traffic_horns[0].audio
                dl_audio, _, _ = auto_tune_slice(horn_raw, scale_midis=scale_midis, strength=1.0, sr=sr)
            downlifter = render_noise_downlifter(dl_audio, duration=2.0, sr=sr)
            d_start = int(sec.start_time * sr)
            dl = min(len(downlifter), total_samples - d_start)
            if dl > 0:
                panned_dl = apply_panning(apply_fade(downlifter[:dl], fade_samples=48) * 0.90, pan=0.0)
                mix[:, d_start:d_start + dl] += panned_dl * 0.60

        # 3. Dynamic foley accents on structural markers
        if "accents" in sec.active_layers:
            acc_slice = accent_bag.next()
            if acc_slice is not None:
                acc_s = int(sec.start_time * sr)
                al = min(len(acc_slice.audio), total_samples - acc_s)
                if al > 0:
                    acc_audio = apply_slice_envelope(acc_slice.audio[:al], attack_ms=4.0, release_ms=10.0, sr=sr)
                    panned_acc = apply_panning(apply_fade(acc_audio, fade_samples=48) * 0.85, pan=rng.uniform(-0.3, 0.3))
                    mix[:, acc_s:acc_s + al] += panned_acc * 0.50

    # 10. Clean Mastering Chain (LUFS -14.0, True Peak Limiter -0.5 dB)
    if on_progress:
        on_progress(94, "Mastering audio (LUFS -14 true peak limiter) & scoring...")

    # Safety soft saturation limiter to guarantee zero summing overflow or distortion before mastering
    pk_mix = float(np.max(np.abs(mix)))
    if pk_mix > 1.25:
        mix = (np.tanh(mix * 0.80) / np.tanh(0.80 * 1.25) * 1.25).astype(np.float32)

    mastered = master_audio(mix, target_lufs=-14.0, target_peak_db=-0.5, sr=sr)

    # 11. Objective Quality Scoring
    score = score_composition(
        output_audio=mastered,
        source_audio=prep.mono,
        source_usage_ratio=1.00,
        synthetic_audio_ratio=0.00,
        sr=sr
    )

    # Dynamic contextual stem descriptions reflecting smart extraction & artist profile
    lead_name = _lead_style.replace('_', ' ').title()
    bass_name = _bass_style.replace('_', ' ').title()
    groove_name = artist_profile.groove_type.replace('_', ' ').title()

    is_vocal = bool(smart_profile and (getattr(smart_profile, 'autotune_enabled', False) or getattr(smart_profile, 'has_speech_or_vocal', False)))
    is_hum = bool(smart_profile and getattr(smart_profile, 'has_humming', False))
    is_beatbox = bool(smart_profile and getattr(smart_profile, 'has_beatbox', False))
    is_traffic = bool(smart_profile and getattr(smart_profile, 'has_traffic_or_engine', False))

    if is_beatbox:
        drum_desc = f"Authentic Vocal Beatbox Kit ({groove_name})"
    else:
        drum_desc = f"Procedural Drum Groove ({groove_name})"

    if is_traffic:
        bed_desc = f"Sidechained Urban Traffic & Engine Bed ({scale.name} Resonated)"
    else:
        bed_desc = "Atmospheric Source Recording Bed (Rhythmic Pumped)"

    if is_classic_vocal:
        vocal_desc = "Classic Electro-Pop Vocal Fusion (Speech/words integrated into rhythmic bed, lead hook & chops)"
        drum_desc = "Four-on-the-Floor Kick, Pop Claps, Disco Open Hats & Timbaland Source Stutters"
        bass_desc = "Rolling 16th-Note Electro-Pop Synth Bassline (Poker Face & Promiscuous Style)"
        lead_desc = f"Anthemic Pop Earworm Lead Hook ({lead_name})"
        bed_desc = "Pumping Spoken Voice & Atmospheric Bed (122 BPM Sidechained)"
    elif not has_vocal_content:
        vocal_desc = "Pure Instrumental Arrangement (Source transformed to Chords, Bass & Drums)"
    elif has_source_horn_stabs:
        vocal_desc = f"Scale Auto-Tuned Traffic Horn Stabs ({scale.name}) — Transformed City Brass Hook"
    elif use_lead_vocal_take:
        vocal_desc = f"Lead Vocal Track: Full Phrase Auto-Tuned ({scale.name}) — Uncut Lyrical Intelligibility"
    elif is_hum:
        vocal_desc = f"Scale Auto-Tuned Harmonized Vocal Hum ({scale.name})"
    elif is_vocal:
        vocal_desc = f"Scale Auto-Tuned Speech Chops ({scale.name}) — Catchy Vocal Hooks"
    else:
        vocal_desc = f"Tuned Syllabic Vocal/Source Chops ({scale.name})"

    bass_desc = f"Deep Synthesized Bassline ({bass_name})"
    lead_desc = f"Procedural Melodic Hook ({lead_name})"

    stems_info = {
        "Drums": drum_desc,
        "Bass": bass_desc,
        "Chords": f"Dynamic 4-Chord Resonant Progression ({scale.name})",
        "Melody": lead_desc,
        "Vocal Hook": vocal_desc,
        "Bed": bed_desc,
        "Accents": "Auto-Tuned Horn & Impact Sweeps" if is_traffic else "Dynamic Noise Riser & Impact Sweeps",
        "Intro Tag": "Auto-Tuned Source Intro Hook" if (is_vocal or is_hum) else "Authentic Source Audio Intro Anchor"
    }

    palette_info = {
        "impacts": len(palette.impacts),
        "pulses": len(palette.pulses),
        "movements": len(palette.movements),
        "textures": len(palette.textures),
        "drones": len(palette.drones),
        "ambience": len(palette.ambience),
        "accents": len(palette.accents),
        "vocal_chops": len(palette.vocal_chops),
        "full_vocal_phrases": len(getattr(palette, 'full_vocal_phrases', [])),
        "beatbox_kicks": len(palette.beatbox_kicks),
        "beatbox_snares": len(palette.beatbox_snares),
        "beatbox_hats": len(palette.beatbox_hats),
        "traffic_horns": len(palette.traffic_horns),
        "humming_slices": len(palette.humming_slices),
        "total_slices": palette.total_slices_extracted,
        "chronological_slices": len(palette.chronological_slices)
    }

    return CompositionResult(
        audio=mastered,
        sr=sr,
        duration=round(total_duration, 2),
        seed=seed,
        scale=scale,
        tempo_bpm=bpm,
        arrangement=arrangement,
        score=score,
        stems_info=stems_info,
        palette_info=palette_info,
        artist_name=artist_profile.name,
        artist_id=artist_profile.id,
        artist_track_hint=artist_profile.track_title_hint,
        cycle_reset=cycle_reset,
        style_name=artist_profile.display_name,
        style_desc=artist_profile.vibe,
        smart_profile=smart_profile
    )


def generate_candidates(
    prep: PreprocessedAudio,
    analysis: CompleteAnalysis,
    base_seed: Optional[int] = None,
    beat_preference: str = "pop",
    energy_preference: str = "low",
    vocal_mode: str = "auto",
    num_candidates: int = 1,
    on_progress: Optional[Any] = None,
    target_duration: float = 30.0,
    played_artists: Optional[List[str]] = None,
    preferred_artist_id: Optional[str] = None
) -> Tuple[CompositionResult, List[CompositionResult]]:
    """Generates candidates with independent seeds and distinct artist profiles. Optimized for speed and low RAM."""
    if base_seed is None:
        base_seed = generate_seed()

    import gc
    import os

    # On Render/low-perf containers reduce upfront work while keeping full quality output
    _is_low_perf = bool(
        os.environ.get("RENDER")
        or os.environ.get("USE_TMP_STORAGE")
        or os.environ.get("LOW_PERF")
    )
    _slice_count = 24 if _is_low_perf else 36
    _pad_duration = min(target_duration, 24.0) if _is_low_perf else target_duration

    # Pre-extract palette once and reuse across all candidates
    if on_progress:
        on_progress(54, "Forging source palette & transient micro-chops...")
    palette = build_source_palette(
        audio=prep.mono,
        sr=prep.sr,
        onset_samples=analysis.rhythm.onset_samples,
        target_slice_count=_slice_count,
        smart_profile=getattr(analysis, 'smart_profile', None)
    )

    # Pre-render shared pad once across candidates
    if on_progress:
        on_progress(60, "Synthesizing granular ambient cloud & pad...")
    shared_pad = create_granular_pad(
        prep.mono,
        target_duration=_pad_duration,
        semitone_shift=0.0,
        grain_duration=0.16,
        density=12.0,
        sr=prep.sr,
        stereo_spread=True
    )

    seeds = [base_seed]
    for _ in range(num_candidates - 1):
        seeds.append(generate_seed())

    candidates: List[CompositionResult] = []
    accumulated_played = list(played_artists or [])
    for idx, s in enumerate(seeds):
        if on_progress:
            pct = 64 + int((idx / max(1, num_candidates)) * 10)
            on_progress(pct, f"Procedurally synthesizing candidate {idx + 1} of {num_candidates}...")
        cand_pref = preferred_artist_id if idx == 0 else None
        cand = render_candidate_composition(
            prep=prep,
            analysis=analysis,
            seed=s,
            beat_preference=beat_preference,
            energy_preference=energy_preference,
            vocal_mode=vocal_mode,
            palette=palette,
            shared_pad=shared_pad,
            on_progress=on_progress,
            target_duration=target_duration,
            exclude_artist_ids=accumulated_played,
            preferred_artist_id=cand_pref
        )
        candidates.append(cand)
        accumulated_played.append(cand.artist_id)
        gc.collect()
        time.sleep(0.01)  # Yield CPU slice to OS scheduler to prevent UI stutter

    candidates.sort(key=lambda c: c.score.total_score, reverse=True)
    return candidates[0], candidates


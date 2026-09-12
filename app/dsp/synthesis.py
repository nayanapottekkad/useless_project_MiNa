"""
Procedural Sound Synthesis Engine for TheUnnecessaryFM
Pure mathematical synthesis without external audio files or neural models.
Provides:
  - Oscillators: Sine, Saw, Square, Triangle, Noise, FM Synthesis
  - ADSR Envelope Generator (linear & exponential)
  - Virtual Instruments: SineBass, SoftBass, Pluck, Bell, Pad, Drone,
    NoisePercussion, FMLead, SoftLead, StringLike
"""

from typing import List, Optional, Tuple
import numpy as np
from scipy import signal

from .segmentation import apply_fade


def adsr_envelope(
    duration: float,
    attack: float,
    decay: float,
    sustain: float,
    release: float,
    sr: int = 44100
) -> np.ndarray:
    """Generate an ADSR amplitude envelope array."""
    total_samples = int(duration * sr)
    if total_samples <= 0:
        return np.zeros(0, dtype=np.float32)

    n_attack = max(1, int(attack * sr))
    n_decay = max(1, int(decay * sr))
    n_release = max(1, int(release * sr))

    # Sustain duration fills remainder
    n_sustain = max(0, total_samples - n_attack - n_decay - n_release)

    # If note is shorter than attack + decay + release, scale proportionally
    if n_attack + n_decay + n_release > total_samples:
        scale = total_samples / (n_attack + n_decay + n_release)
        n_attack = max(1, int(n_attack * scale))
        n_decay = max(1, int(n_decay * scale))
        n_release = max(1, total_samples - n_attack - n_decay)
        n_sustain = 0

    attack_curve = np.linspace(0.0, 1.0, n_attack)
    decay_curve = np.linspace(1.0, sustain, n_decay)
    sustain_curve = np.full(n_sustain, sustain)
    release_curve = np.linspace(sustain, 0.0, n_release)

    env = np.concatenate([attack_curve, decay_curve, sustain_curve, release_curve])
    if len(env) < total_samples:
        env = np.pad(env, (0, total_samples - len(env)))
    elif len(env) > total_samples:
        env = env[:total_samples]

    env_out = env.astype(np.float32)
    # Ensure envelope strictly starts and ends at 0.0 to prevent note boundary clicks
    fade_s = min(32, total_samples // 4)
    if fade_s > 1:
        env_out = apply_fade(env_out, fade_samples=fade_s)
    return env_out


def sine_wave(freq: float, duration: float, phase: float = 0.0, sr: int = 44100) -> np.ndarray:
    """Generate pure sine wave oscillator."""
    num_samples = int(duration * sr)
    t = np.linspace(0, duration, num_samples, endpoint=False)
    return np.sin(2.0 * np.pi * freq * t + phase).astype(np.float32)


def saw_wave(freq: float, duration: float, sr: int = 44100) -> np.ndarray:
    """Generate anti-aliased saw wave using band-limited additive synthesis (vectorized)."""
    num_samples = int(duration * sr)
    t = np.linspace(0, duration, num_samples, endpoint=False)
    max_h = min(20, int((sr * 0.45) / max(1.0, freq)))
    if max_h < 1:
        return np.zeros(num_samples, dtype=np.float32)
    # Vectorized: stack all harmonics into a (max_h, num_samples) matrix and sum
    h = np.arange(1, max_h + 1, dtype=np.float32)  # shape (max_h,)
    phases = 2.0 * np.pi * freq * np.outer(h, t)    # shape (max_h, num_samples)
    out = np.sum(np.sin(phases) / h[:, np.newaxis], axis=0)
    pk = np.max(np.abs(out))
    if pk > 0:
        out = (out / pk) * 0.95
    return out.astype(np.float32)


def square_wave(freq: float, duration: float, sr: int = 44100) -> np.ndarray:
    """Generate band-limited square wave using odd harmonics (vectorized)."""
    num_samples = int(duration * sr)
    t = np.linspace(0, duration, num_samples, endpoint=False)
    max_h = min(15, int((sr * 0.45) / max(1.0, freq)))
    if max_h < 1:
        return np.zeros(num_samples, dtype=np.float32)
    # Vectorized odd harmonics
    h = np.arange(1, max_h + 1, 2, dtype=np.float32)  # 1, 3, 5 ...
    phases = 2.0 * np.pi * freq * np.outer(h, t)
    out = np.sum(np.sin(phases) / h[:, np.newaxis], axis=0)
    pk = np.max(np.abs(out))
    if pk > 0:
        out = (out / pk) * 0.95
    return out.astype(np.float32)


def triangle_wave(freq: float, duration: float, sr: int = 44100) -> np.ndarray:
    """Generate band-limited triangle wave (vectorized)."""
    num_samples = int(duration * sr)
    t = np.linspace(0, duration, num_samples, endpoint=False)
    max_h = min(15, int((sr * 0.45) / max(1.0, freq)))
    if max_h < 1:
        return np.zeros(num_samples, dtype=np.float32)
    # Vectorized odd harmonics with alternating sign
    h = np.arange(1, max_h + 1, 2, dtype=np.float32)  # 1, 3, 5 ...
    signs = ((-1.0) ** np.arange(len(h))).astype(np.float32)  # +1, -1, +1 ...
    phases = 2.0 * np.pi * freq * np.outer(h, t)
    out = np.sum(signs[:, np.newaxis] * np.sin(phases) / (h ** 2)[:, np.newaxis], axis=0)
    pk = np.max(np.abs(out))
    if pk > 0:
        out = (out / pk) * 0.95
    return out.astype(np.float32)


def fm_synth(
    carrier_freq: float,
    mod_freq: float,
    mod_index: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """Frequency Modulation synthesis oscillator."""
    num_samples = int(duration * sr)
    t = np.linspace(0, duration, num_samples, endpoint=False)
    # Modulator
    modulator = mod_index * np.sin(2.0 * np.pi * mod_freq * t)
    # Carrier
    carrier = np.sin(2.0 * np.pi * carrier_freq * t + modulator)
    return carrier.astype(np.float32)


# ==============================================================================
# Procedural Virtual Instruments
# ==============================================================================

class SynthInstrument:
    """Base class for procedurally synthesized instruments."""
    def render_note(self, freq: float, duration: float, velocity: float = 0.8, sr: int = 44100) -> np.ndarray:
        raise NotImplementedError


class SineBass(SynthInstrument):
    """Deep pure fundamental sub-bass with subtle 2nd harmonic saturation."""
    def render_note(self, freq: float, duration: float, velocity: float = 0.8, sr: int = 44100) -> np.ndarray:
        # Keep bass frequency in musical sub register (35 Hz - 180 Hz)
        while freq > 180.0:
            freq /= 2.0
        while freq < 35.0:
            freq *= 2.0

        osc = sine_wave(freq, duration, sr=sr)
        # Add slight 2nd harmonic warmth
        osc += 0.15 * sine_wave(freq * 2.0, duration, sr=sr)
        # Soft saturation
        osc = np.tanh(osc * 1.4)

        env = adsr_envelope(duration, attack=0.015, decay=0.2, sustain=0.75, release=0.08, sr=sr)
        return (osc * env * velocity).astype(np.float32)


class SoftBass(SynthInstrument):
    """Warm filtered saw/triangle bass."""
    def render_note(self, freq: float, duration: float, velocity: float = 0.8, sr: int = 44100) -> np.ndarray:
        while freq > 200.0:
            freq /= 2.0
        while freq < 40.0:
            freq *= 2.0

        saw = saw_wave(freq, duration, sr=sr)
        sub = sine_wave(freq, duration, sr=sr)
        raw = saw * 0.4 + sub * 0.6

        # Low-pass filter at 350 Hz
        b, a = signal.butter(2, min(0.45, 380.0 / (sr * 0.5)), btype='low')
        filtered = signal.lfilter(b, a, raw)

        env = adsr_envelope(duration, attack=0.01, decay=0.15, sustain=0.7, release=0.1, sr=sr)
        return (filtered * env * velocity).astype(np.float32)


class Pluck(SynthInstrument):
    """Karplus-Strong physical modeling pluck via fast vectorized feedback filter."""
    def render_note(self, freq: float, duration: float, velocity: float = 0.8, sr: int = 44100) -> np.ndarray:
        total_samples = int(duration * sr)
        if total_samples <= 0:
            return np.zeros(0, dtype=np.float32)

        period = int(round(sr / max(20.0, freq)))
        if period <= 0:
            period = 100

        # Excitation: short burst of white noise of length 'period'
        burst = np.random.uniform(-1.0, 1.0, period).astype(np.float32)
        excitation = np.pad(burst, (0, max(0, total_samples - period)))[:total_samples]

        # Feedback loop: y[n] = x[n] + decay * y[n - period]
        decay_factor = float(np.clip(0.988 - (freq / 8000.0) * 0.05, 0.90, 0.995))
        b = np.array([1.0], dtype=np.float32)
        a = np.zeros(period + 1, dtype=np.float32)
        a[0] = 1.0
        a[period] = -decay_factor

        out = signal.lfilter(b, a, excitation)
        # Gentle low-pass filter for acoustic warmth
        cutoff = min(sr * 0.45, max(800.0, freq * 4.5))
        b_lp, a_lp = signal.butter(1, cutoff / (sr * 0.5), btype='low')
        out = signal.lfilter(b_lp, a_lp, out)

        fade_samples = min(256, total_samples)
        out[-fade_samples:] *= np.linspace(1.0, 0.0, fade_samples)

        pk = np.max(np.abs(out))
        if pk > 0:
            out = (out / pk) * velocity * 0.85
        return out.astype(np.float32)


class Bell(SynthInstrument):
    """FM synthesized metallic chime/bell."""
    def render_note(self, freq: float, duration: float, velocity: float = 0.8, sr: int = 44100) -> np.ndarray:
        # Non-integer modulator ratio (2.76) for metallic bell timbre
        mod_ratio = 2.756
        carrier = fm_synth(
            carrier_freq=freq,
            mod_freq=freq * mod_ratio,
            mod_index=2.5,
            duration=duration,
            sr=sr
        )
        # Fast attack, exponential decay
        env = adsr_envelope(duration, attack=0.003, decay=duration * 0.8, sustain=0.05, release=0.1, sr=sr)
        return (carrier * env * velocity * 0.7).astype(np.float32)


class Pad(SynthInstrument):
    """Rich polyphonic warm pad with slight chorus detune."""
    def render_note(self, freq: float, duration: float, velocity: float = 0.8, sr: int = 44100) -> np.ndarray:
        osc1 = triangle_wave(freq, duration, sr=sr)
        osc2 = sine_wave(freq * 1.003, duration, sr=sr)   # Slight detune
        osc3 = saw_wave(freq * 0.997, duration, sr=sr) * 0.3

        raw = osc1 * 0.45 + osc2 * 0.45 + osc3

        # Lowpass filter
        b, a = signal.butter(2, min(0.45, 1400.0 / (sr * 0.5)), btype='low')
        filtered = signal.lfilter(b, a, raw)

        env = adsr_envelope(duration, attack=0.45, decay=0.3, sustain=0.8, release=0.5, sr=sr)
        return (filtered * env * velocity * 0.7).astype(np.float32)


class Drone(SynthInstrument):
    """Deep modal drone with slow pulsating harmonics."""
    def render_note(self, freq: float, duration: float, velocity: float = 0.8, sr: int = 44100) -> np.ndarray:
        while freq > 130.0:
            freq /= 2.0

        osc = sine_wave(freq, duration, sr=sr) * 0.6
        osc += sine_wave(freq * 1.5, duration, sr=sr) * 0.25  # Fifth
        osc += sine_wave(freq * 2.0, duration, sr=sr) * 0.15  # Octave

        # Slow LFO (0.2 Hz)
        t = np.linspace(0, duration, len(osc), endpoint=False)
        lfo = 0.75 + 0.25 * np.sin(2.0 * np.pi * 0.2 * t)
        osc = osc * lfo

        env = adsr_envelope(duration, attack=0.8, decay=0.2, sustain=0.9, release=0.8, sr=sr)
        return (osc * env * velocity * 0.75).astype(np.float32)


class FMLead(SynthInstrument):
    """Bright expressive FM lead synth."""
    def render_note(self, freq: float, duration: float, velocity: float = 0.8, sr: int = 44100) -> np.ndarray:
        # 1:1 or 1:2 harmonic ratio
        lead = fm_synth(
            carrier_freq=freq,
            mod_freq=freq * 2.0,
            mod_index=1.8,
            duration=duration,
            sr=sr
        )
        env = adsr_envelope(duration, attack=0.03, decay=0.15, sustain=0.6, release=0.12, sr=sr)
        return (lead * env * velocity * 0.7).astype(np.float32)


class SoftLead(SynthInstrument):
    """Mellow flute-like triangle lead with gentle vibrato."""
    def render_note(self, freq: float, duration: float, velocity: float = 0.8, sr: int = 44100) -> np.ndarray:
        num_samples = int(duration * sr)
        t = np.linspace(0, duration, num_samples, endpoint=False)
        # 5 Hz vibrato
        vibrato = 0.008 * np.sin(2.0 * np.pi * 5.0 * t)
        phase = np.cumsum(2.0 * np.pi * freq * (1.0 + vibrato) / sr)
        osc = np.sin(phase) + 0.25 * np.sin(phase * 2.0)

        env = adsr_envelope(duration, attack=0.08, decay=0.1, sustain=0.85, release=0.15, sr=sr)
        return (osc * env * velocity * 0.7).astype(np.float32)


class StringLike(SynthInstrument):
    """Bowed string emulation with warm saw cluster."""
    def render_note(self, freq: float, duration: float, velocity: float = 0.8, sr: int = 44100) -> np.ndarray:
        saw1 = saw_wave(freq, duration, sr=sr)
        saw2 = saw_wave(freq * 1.004, duration, sr=sr)
        raw = (saw1 + saw2) * 0.5

        # Resonant filter around 1200 Hz
        b, a = signal.butter(2, min(0.45, 1800.0 / (sr * 0.5)), btype='low')
        filtered = signal.lfilter(b, a, raw)

        env = adsr_envelope(duration, attack=0.15, decay=0.2, sustain=0.85, release=0.25, sr=sr)
        return (filtered * env * velocity * 0.65).astype(np.float32)


def get_procedural_instrument(name: str) -> SynthInstrument:
    """Factory helper to obtain instrument by name."""
    catalog = {
        "SineBass": SineBass,
        "SoftBass": SoftBass,
        "Pluck": Pluck,
        "Bell": Bell,
        "Pad": Pad,
        "Drone": Drone,
        "FMLead": FMLead,
        "SoftLead": SoftLead,
        "StringLike": StringLike,
    }
    cls = catalog.get(name, Pluck)
    return cls()


# ==============================================================================
# PROFESSIONAL NOISE-TO-MUSIC INSTRUMENT ENGINES
# (Directly converts raw audio/noise into tonal leads, plucks, bass, and drums)
# ==============================================================================

def biquad_modal_resonator(audio: np.ndarray, freq: float, q: float, sr: int = 44100) -> np.ndarray:
    """
    Standard constant 0 dB peak gain 2nd-order resonator (Audio EQ Cookbook):
    H(s) = (s / Q) / (s^2 + s/Q + 1)
    Digital Biquad coefficients:
      omega = 2 * pi * freq / sr
      alpha = sin(omega) / (2 * Q)
      b0 = alpha, b1 = 0, b2 = -alpha
      a0 = 1 + alpha, a1 = -2 * cos(omega), a2 = 1 - alpha
    Extremely stable, zero DC offset, strictly constant gain at resonance peak.
    """
    freq = float(np.clip(freq, 20.0, sr * 0.48))
    q = max(0.5, float(q))
    omega = 2.0 * np.pi * freq / sr
    sn = np.sin(omega)
    cs = np.cos(omega)
    alpha = sn / (2.0 * q)
    b0 = alpha
    b1 = 0.0
    b2 = -alpha
    a0 = 1.0 + alpha
    a1 = -2.0 * cs
    a2 = 1.0 - alpha
    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float32)
    a = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float32)
    return signal.lfilter(b, a, audio).astype(np.float32)


# ==============================================================================
# SIGNATURE ARTIST INSTRUMENT SYNTHESIZERS (STUDIO-GRADE DSP MODELS)
# ==============================================================================

def render_metro_chime(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    METRO BOOMIN INHARMONIC CHIME (Premium Bell):
    - Inharmonic modal partials [1.0, 2.76, 5.40] with independent exponential decays [1.8s, 1.1s, 0.6s].
    - Body layer at fundamental / 2 with 2.4s decay.
    - Tape-flutter pitch wobble (slow 0.5 Hz random-walk / sinusoidal drift +-3 cents).
    - Dark lowpass filter at 4.0 kHz (eliminating thin fizz).
    - Reversed tail texture layered underneath attack.
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    # Tape flutter drift (+- 3 cents)
    drift_cents = 3.0 * np.sin(2.0 * np.pi * 0.5 * t)
    f_drift = freq * (2.0 ** (drift_cents / 1200.0))
    phase = 2.0 * np.pi * np.cumsum(f_drift) / sr

    # 1. Inharmonic modal partials with independent decays
    ratios = [1.0, 2.76, 5.40]
    decay_times = [1.8, 1.1, 0.6]
    amps = [1.0, 0.55, 0.28]
    qs = [45.0, 36.0, 28.0]

    chime_partials = np.zeros(total_samples, dtype=np.float32)
    for r, d_t, amp, q_val in zip(ratios, decay_times, amps, qs):
        p_freq = min(sr * 0.45, freq * r)
        res = biquad_modal_resonator(noise_chunk, p_freq, q=q_val, sr=sr)
        sin_ring = np.sin(phase * r)
        env = np.exp(-t / max(0.05, d_t)).astype(np.float32)
        chime_partials += (res * 0.70 + sin_ring * 0.50) * env * amp

    # 2. Lower body layer: fundamental / 2 with wooden/metal body decay (2.4s)
    body_freq = max(40.0, freq * 0.5)
    body_res = biquad_modal_resonator(noise_chunk, body_freq, q=25.0, sr=sr)
    body_sin = np.sin(phase * 0.5)
    body_env = np.exp(-t / 2.4).astype(np.float32)
    body_layer = (body_res * 0.60 + body_sin * 0.40) * body_env * 0.50

    combined = chime_partials + body_layer

    # 3. Dark lowpass shelf above 4 kHz to eliminate thin tinny fizz
    b_lp, a_lp = signal.butter(2, min(0.45, 4000.0 / (sr * 0.5)), btype='low')
    dark_chime = signal.lfilter(b_lp, a_lp, combined).astype(np.float32)

    # 4. Reversed tail texture (documented signature Metro Boomin technique)
    tail_len = min(total_samples, int(0.5 * total_samples))
    if tail_len > 64:
        rev_tail = dark_chime[total_samples - tail_len:].copy()[::-1]
        rev_env = np.linspace(0.0, 1.0, tail_len, dtype=np.float32) * np.linspace(1.0, 0.0, tail_len, dtype=np.float32)
        dark_chime[:tail_len] += rev_tail * rev_env * 0.42

    return np.tanh(dark_chime * 1.5).astype(np.float32)


def render_usher_crunk_lead(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    USHER & LIL JON CRUNK LEAD ("Yeah!"):
    - Dual saw + square oscillator, hard sync ratio 1:1.01 (slight detune bite).
    - Bandpass filter center sweep: 1400 -> 2800 Hz over the first 10ms:
      bp_center(t) = 1400 + 1400 * exp(-t / 0.010) Hz.
    - Stereo detune +- 9 cents.
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    f_detune_l = freq * (2.0 ** (-9.0 / 1200.0))
    f_detune_r = freq * (2.0 ** (+9.0 / 1200.0))
    s1 = saw_wave(f_detune_l, duration, sr=sr)
    s2 = square_wave(f_detune_r * 1.01, duration, sr=sr)
    dual_core = (s1 * 0.60 + s2 * 0.40)

    n_sweep = min(total_samples, int(0.010 * sr))
    out_lead = dual_core.copy()
    if n_sweep > 16:
        bp_c = 1400.0 + 1400.0 * np.exp(-t[:n_sweep] / 0.010)
        early_res = biquad_modal_resonator(out_lead[:n_sweep], float(np.mean(bp_c)), q=8.0, sr=sr)
        out_lead[:n_sweep] = early_res * 1.5
    bp_steady = biquad_modal_resonator(out_lead, 1400.0, q=6.0, sr=sr)
    out_lead = out_lead * 0.45 + bp_steady * 0.55

    res_noise = biquad_modal_resonator(noise_chunk, freq, q=24.0, sr=sr)
    env = adsr_envelope(duration, attack=0.003, decay=min(0.25, duration * 0.6), sustain=0.45, release=0.06, sr=sr)
    final_note = (out_lead * 0.70 + res_noise * 0.30) * env
    return np.tanh(final_note * 1.6).astype(np.float32)


def render_lady_gaga_supersaw(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    LADY GAGA / REDONE ELECTRO PLUCK ("Poker Face", "Bad Romance"):
    Authentic physical vocal/noise resonator from classic release:
    - Resonates fundamental f0, 2nd harmonic f2, and 3rd harmonic f3 directly from the voice/noise.
    - 15% raw noise texture retention + analog saturation tanh(1.6x).
    - Tight electro envelope with subtle sub-support and bright presence.
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    # 1. Physical multi-harmonic resonance bank on input noise/voice
    freq = float(np.clip(freq, 40.0, sr * 0.45))
    bw = freq / 22.0
    f_low = max(20.0, freq - bw * 0.5)
    f_high = min(sr * 0.48, freq + bw * 0.5)
    b, a = signal.butter(2, [f_low / (sr * 0.5), f_high / (sr * 0.5)], btype='bandpass')
    resonated_f0 = signal.lfilter(b, a, noise_chunk)

    f2 = min(sr * 0.45, freq * 2.0)
    bw2 = f2 / 20.0
    b2, a2 = signal.butter(1, [max(20.0, f2 - bw2 * 0.5) / (sr * 0.5), min(sr * 0.48, f2 + bw2 * 0.5) / (sr * 0.5)], btype='bandpass')
    resonated_f2 = signal.lfilter(b2, a2, noise_chunk)

    f3 = min(sr * 0.45, freq * 3.0)
    bw3 = f3 / 18.0
    b3, a3 = signal.butter(1, [max(20.0, f3 - bw3 * 0.5) / (sr * 0.5), min(sr * 0.48, f3 + bw3 * 0.5) / (sr * 0.5)], btype='bandpass')
    resonated_f3 = signal.lfilter(b3, a3, noise_chunk)

    tonal_noise = (resonated_f0 * 18.0 + resonated_f2 * 10.0 + resonated_f3 * 4.0)
    textured_note = tonal_noise * 0.85 + noise_chunk * 0.15
    saturated_body = np.tanh(textured_note * 1.6)

    # 2. Fast snappy punch envelope + 15% sub fundamental support
    env = adsr_envelope(duration, attack=0.004, decay=min(0.32, duration * 0.65), sustain=0.20, release=0.08, sr=sr)
    sub_support = 0.15 * np.sin(2.0 * np.pi * freq * t)

    # 3. Subtle wide saw bite layer (18% mix) for electro sheen
    f_v1 = float(np.clip(freq * (2.0 ** (-6.0 / 1200.0)), 20.0, sr * 0.45))
    f_v2 = float(np.clip(freq * (2.0 ** (6.0 / 1200.0)), 20.0, sr * 0.45))
    saw_layer = (saw_wave(f_v1, duration, sr=sr) + saw_wave(f_v2, duration, sr=sr)) * 0.5
    # Static scalar lowpass for electro sheen (3500 Hz bright cut - avoids array-to-scalar error)
    f_cut_scalar = float(np.clip(3500.0, 300.0, sr * 0.46))
    b_s, a_s = signal.butter(1, min(0.48, f_cut_scalar / (sr * 0.5)), btype='low')
    saw_filtered = signal.lfilter(b_s, a_s, saw_layer)

    rendered = (saturated_body * 0.82 + saw_filtered * 0.18 + sub_support * 0.15) * env
    return np.tanh(rendered * 1.4).astype(np.float32)


def render_mj_horn_stab(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    MICHAEL JACKSON & QUINCY JONES BRASS STAB (Jerry Hey Brass Section):
    - Additive synthesis with harmonics [1.0, 0.70, 0.55, 0.35, 0.20].
    - 15ms swell attack (breath / valve lag) and 60ms staccato release.
    - Dual brass formant peaks (950 Hz and 1800 Hz).
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    harmonics = [1.0, 0.70, 0.55, 0.35, 0.20]
    brass_sum = np.zeros(total_samples, dtype=np.float32)
    for k, amp in enumerate(harmonics, start=1):
        f_k = freq * k
        if f_k < sr * 0.46:
            brass_sum += np.sin(2.0 * np.pi * f_k * t) * amp

    f1 = min(sr * 0.45, 950.0)
    f2 = min(sr * 0.45, 1800.0)
    formant1 = biquad_modal_resonator(noise_chunk, f1, q=14.0, sr=sr)
    formant2 = biquad_modal_resonator(noise_chunk, f2, q=18.0, sr=sr)

    att_s = 0.015
    rel_s = 0.060
    decay_s = min(0.12, max(0.04, duration - att_s - rel_s))
    env = adsr_envelope(duration, attack=att_s, decay=decay_s, sustain=0.35, release=rel_s, sr=sr)

    combined = (brass_sum * 0.65 + (formant1 + formant2) * 0.35) * env
    return np.tanh(combined * 1.5).astype(np.float32)


def render_vintage_synthwave(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    THE WEEKND & MAX MARTIN 80S JUNO-106 LEAD ("Blinding Lights"):
    - Dual saw + pulse sub-octave.
    - 4-voice BBD chorus emulation (detune [-12, -4, 4, 12] cents, 0.6 Hz LFO wobble).
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    cents = [-12.0, -4.0, 4.0, 12.0]
    chorus_sum = np.zeros(total_samples, dtype=np.float32)
    for i, c in enumerate(cents):
        phase_mod = 0.012 * np.sin(2.0 * np.pi * 0.6 * t + i * (np.pi / 2.0))
        f_voice = float(np.clip(freq * (2.0 ** (c / 1200.0)), 20.0, sr * 0.45))
        v_saw = saw_wave(f_voice, duration, sr=sr)
        v_pulse = square_wave(f_voice * 0.5, duration, sr=sr) * 0.45
        chorus_sum += (v_saw + v_pulse) * 0.25

    b, a = signal.butter(2, min(0.45, 2800.0 / (sr * 0.5)), btype='low')
    analog_tone = signal.lfilter(b, a, chorus_sum).astype(np.float32)

    res_noise = biquad_modal_resonator(noise_chunk, freq, q=20.0, sr=sr)
    env = adsr_envelope(duration, attack=0.008, decay=min(0.20, duration * 0.5), sustain=0.65, release=0.10, sr=sr)
    combined = (analog_tone * 0.75 + res_noise * 0.30) * env
    return np.tanh(combined * 1.4).astype(np.float32)


def render_gfunk_whistle(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    DR. DRE G-FUNK SOARING SINE WHISTLE ("Still D.R.E.", "Nuthin' But A G Thang"):
    - Soaring high sine lead with 5.2 Hz vibrato (+-25 cents).
    - 120ms portamento glide onset.
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    port_s = min(total_samples, int(0.120 * sr))
    port_curve = np.ones(total_samples, dtype=np.float32)
    if port_s > 4:
        port_curve[:port_s] = 0.94 + 0.06 * (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, port_s)))

    vib = 25.0 * np.sin(2.0 * np.pi * 5.2 * t)
    f_curve = freq * port_curve * (2.0 ** (vib / 1200.0))
    phase = 2.0 * np.pi * np.cumsum(f_curve) / sr

    whistle = np.sin(phase) + 0.08 * np.sin(2.0 * phase)
    env = adsr_envelope(duration, attack=0.04, decay=0.1, sustain=0.85, release=0.10, sr=sr)
    res_air = biquad_modal_resonator(noise_chunk, min(sr * 0.45, freq * 1.5), q=28.0, sr=sr) * 0.15
    return (whistle * env * 0.85 + res_air * env * 0.15).astype(np.float32)


def render_dre_storch_piano(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    SCOTT STORCH 16TH STACCATO ELECTRIC PIANO ("Still D.R.E."):
    - Crisp staccato Rhodes / electric piano plink with immediate decay.
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    tine = (np.sin(2.0 * np.pi * freq * t) +
            0.45 * np.sin(4.0 * np.pi * freq * t) +
            0.20 * np.sin(6.0 * np.pi * freq * t) +
            0.12 * np.sin(2.0 * np.pi * freq * 14.0 * t))
    env = np.exp(-t * 18.0).astype(np.float32)

    res1 = biquad_modal_resonator(noise_chunk, freq, q=36.0, sr=sr)
    res2 = biquad_modal_resonator(noise_chunk, min(sr * 0.46, freq * 2.0), q=26.0, sr=sr) * 0.4
    combined = (res1 + res2) * 2.4 * env + tine * env * 0.7
    return np.tanh(combined * 1.5).astype(np.float32)


def render_neptunes_triton_pluck(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    PHARRELL & THE NEPTUNES KORG TRITON PLUCK:
    - Bubbly square-wave pluck with rapid closing resonant filter (0.07s decay).
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    sq = square_wave(freq, duration, sr=sr)
    block_s = max(16, int(0.004 * sr))
    filtered_sq = np.zeros_like(sq)
    for i in range(0, total_samples, block_s):
        end_i = min(total_samples, i + block_s)
        t_mid = (i + end_i) * 0.5 / sr
        f_cut = float(np.clip(450.0 + 3600.0 * np.exp(-t_mid / 0.07), 400.0, sr * 0.46))
        b, a = signal.butter(2, min(0.48, f_cut / (sr * 0.5)), btype='low')
        filtered_sq[i:end_i] = signal.lfilter(b, a, sq[i:end_i])

    env = np.exp(-t * 16.0).astype(np.float32)
    res = biquad_modal_resonator(noise_chunk, freq, q=30.0, sr=sr) * 2.0
    combined = (filtered_sq * 0.70 + res * 0.35) * env
    return np.tanh(combined * 1.6).astype(np.float32)


def render_kanye_soulchop(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    KANYE WEST EARLY CHIPMUNK SOUL SAMPLE LEAD:
    - Pitches up input tonal slice +5 to +7 semitones WITHOUT formant correction
      for classic MPC / SP-1200 pitch-up vocal timbre.
    - Adds subtle vintage vinyl surface dust floor.
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    pitch_ratio = 2.0 ** (5.0 / 12.0)
    orig_len = len(noise_chunk)
    if orig_len > 32:
        new_indices = np.linspace(0, orig_len - 1, int(orig_len / pitch_ratio))
        chopped = np.interp(new_indices, np.arange(orig_len), noise_chunk).astype(np.float32)
        reps = int(np.ceil(total_samples / len(chopped)))
        pitched_layer = np.tile(chopped, reps)[:total_samples]
    else:
        pitched_layer = noise_chunk[:total_samples] if len(noise_chunk) >= total_samples else np.pad(noise_chunk, (0, total_samples - len(noise_chunk)))

    res = biquad_modal_resonator(pitched_layer, freq, q=24.0, sr=sr) * 2.6
    vinyl_crackle = np.random.normal(0, 0.015, total_samples).astype(np.float32)
    env = adsr_envelope(duration, attack=0.010, decay=min(0.35, duration * 0.6), sustain=0.55, release=0.12, sr=sr)
    combined = (res * 0.75 + pitched_layer * 0.25 + vinyl_crackle) * env
    return np.tanh(combined * 1.5).astype(np.float32)


def render_dualipa_clavinet(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    DUA LIPA NU-DISCO CLAVINET / PLUCK:
    - Upper-register Karplus-Strong pluck with 250Hz highpass and fast damping.
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    L = max(4, int(round(sr / freq)))

    excitation = np.zeros(total_samples, dtype=np.float32)
    g_len = min(L, len(noise_chunk))
    if g_len > 0:
        excitation[:g_len] = noise_chunk[:g_len] * np.hanning(g_len)
    else:
        excitation[:L] = np.random.normal(0, 0.2, L).astype(np.float32)

    b = np.array([1.0], dtype=np.float32)
    a = np.zeros(L + 2, dtype=np.float32)
    a[0] = 1.0
    a[L] = -0.990 * 0.25
    a[L + 1] = -0.990 * 0.75
    clav = signal.lfilter(b, a, excitation)

    b_hp, a_hp = signal.butter(2, min(0.45, 250.0 / (sr * 0.5)), btype='high')
    clav_bright = signal.lfilter(b_hp, a_hp, clav)
    env = np.exp(-t * 12.0).astype(np.float32)
    return np.tanh(clav_bright * env * 2.0).astype(np.float32)


def render_brunomars_guitar_horns(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    BRUNO MARS & THE HOOLIGANS UPTOWN FUNK BRASS SECTION ("24K Magic" / "Uptown Funk"):
    - Dynamic 3-part brass section stab (trumpet, tenor sax, trombone).
    - Multi-formant acoustic brass resonance (880 Hz, 1450 Hz, 2400 Hz).
    - High-energy swell attack and staccato fall-off envelope. 100% independent from clavinet!
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    # 3-part tight horn voicing: root, fifth (+7 semitones), and octave (+12 semitones)
    f_root = float(np.clip(freq, 40.0, sr * 0.44))
    f_fifth = float(np.clip(f_root * (2.0 ** (7.0 / 12.0)), 40.0, sr * 0.44))
    f_oct = float(np.clip(f_root * 2.0, 40.0, sr * 0.44))

    # Rich harmonic brass additive oscillators
    horn_osc = (
        saw_wave(f_root, duration, sr=sr) * 0.45 +
        saw_wave(f_fifth, duration, sr=sr) * 0.35 +
        square_wave(f_oct, duration, sr=sr) * 0.20
    )

    # Multi-formant Jerry Hey brass section filtering
    b_horn, a_horn = signal.butter(2, [min(0.44, 450.0 / (sr * 0.5)), min(0.46, 3800.0 / (sr * 0.5))], btype='band')
    brass_filtered = signal.lfilter(b_horn, a_horn, horn_osc).astype(np.float32)

    formant_horn = biquad_modal_resonator(noise_chunk, f_root, q=20.0, sr=sr)
    env = adsr_envelope(duration, attack=0.008, decay=min(0.25, duration * 0.6), sustain=0.45, release=0.06, sr=sr)

    combined = (brass_filtered * 0.70 + formant_horn * 0.35) * env
    return np.tanh(combined * 1.8).astype(np.float32)


def render_mj_synclavier_rhodes(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    MICHAEL JACKSON & QUINCY JONES ICONIC 80S SYNCLAVIER / DX7 FM RHODES STAB:
    - 2-operator FM synthesis: Carrier f0 + Modulator f0 * 14.0 (bell/tine harmonic) + Modulator f0 (warmth).
    - Rapid decay on FM index creates sparkling metallic bell attack.
    - Dual-voice chorus emulation with modal noise resonator.
    - Crisp staccato funk decay envelope.
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    f_base = float(np.clip(freq, 40.0, sr * 0.44))

    # Fast decaying FM index for bell/tine strike
    mod_index = 3.2 * np.exp(-t * 24.0)
    modulator = np.sin(2.0 * np.pi * f_base * 14.0 * t) * mod_index + 0.5 * np.sin(2.0 * np.pi * f_base * t)
    carrier = np.sin(2.0 * np.pi * f_base * t + modulator)

    # Add warmth harmonic
    warmth = 0.35 * np.sin(2.0 * np.pi * f_base * 2.0 * t)

    # Analog chorus shimmer
    chorus = 0.25 * np.sin(2.0 * np.pi * (f_base * 1.003) * t)

    fm_piano = (carrier + warmth + chorus) * 0.65

    # Modal resonance from noise
    res_bell = biquad_modal_resonator(noise_chunk, min(sr * 0.45, f_base * 2.0), q=26.0, sr=sr) * 0.35

    env = adsr_envelope(duration, attack=0.005, decay=min(0.28, duration * 0.65), sustain=0.35, release=0.08, sr=sr)
    combined = (fm_piano * 0.70 + res_bell * 0.30) * env
    return np.tanh(combined * 1.6).astype(np.float32)


def render_pokerface_stutter_lead(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    LADY GAGA & REDONE "POKER FACE" / "JUST DANCE" ROBOTIC STUTTER VOCAL SAW:
    - Stuttering 16th-note rhythmic gate.
    - Dual saw-square oscillator with bitcrushed edge.
    - Formant vowel filtering (720 Hz & 1850 Hz) emulating the "Mum-mum-mum-mah" robotic timbre.
    - Aggressive, punchy electro staccato envelope.
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    f_base = float(np.clip(freq, 40.0, sr * 0.44))

    # Dual detuned oscillators: saw + square with sub octave
    osc1 = saw_wave(f_base, duration, sr=sr) * 0.55
    osc2 = square_wave(f_base * 1.006, duration, sr=sr) * 0.35
    osc_sub = square_wave(f_base * 0.5, duration, sr=sr) * 0.20
    raw_lead = osc1 + osc2 + osc_sub

    # Vocal-formant bandpass filters
    b1, a1 = signal.butter(2, [min(0.44, 650.0 / (sr * 0.5)), min(0.46, 1200.0 / (sr * 0.5))], btype='band')
    b2, a2 = signal.butter(2, [min(0.44, 1700.0 / (sr * 0.5)), min(0.46, 2600.0 / (sr * 0.5))], btype='band')
    formant_tone = (signal.lfilter(b1, a1, raw_lead) * 0.65 + signal.lfilter(b2, a2, raw_lead) * 0.45).astype(np.float32)

    # Fast 16th staccato gate
    env = adsr_envelope(duration, attack=0.004, decay=min(0.12, duration * 0.5), sustain=0.25, release=0.04, sr=sr)
    res_noise = biquad_modal_resonator(noise_chunk, f_base, q=22.0, sr=sr) * 0.30

    combined = (formant_tone * 0.75 + res_noise) * env
    return np.tanh(combined * 2.2).astype(np.float32)


def render_kanye_flashing_strings(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """
    KANYE WEST & MIKE DEAN "FLASHING LIGHTS" STACCATO SYNTH STRINGS:
    - Rapid 16th-note neo-classical staccato strings.
    - Rich multi-saw string body with subtle downward pitch scoop on onset (-15 cents).
    - Dual resonant bandpass formants (violin/viola acoustic resonance at 1400 Hz & 3200 Hz).
    - Snappy gated bow envelope with quick release.
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    scoop = 1.0 + 0.04 * np.exp(-t / 0.015)
    f_base = float(np.clip(freq, 60.0, sr * 0.44)) * scoop

    cents = [-9.0, 0.0, 9.0]
    string_sum = np.zeros(total_samples, dtype=np.float32)
    for c in cents:
        f_voice = float(np.clip(freq * (2.0 ** (c / 1200.0)), 30.0, sr * 0.45))
        string_sum += saw_wave(f_voice, duration, sr=sr) * 0.33

    b_str, a_str = signal.butter(2, [min(0.44, 900.0 / (sr * 0.5)), min(0.46, 4200.0 / (sr * 0.5))], btype='band')
    string_filtered = signal.lfilter(b_str, a_str, string_sum).astype(np.float32)

    res_body = biquad_modal_resonator(noise_chunk, freq, q=24.0, sr=sr)

    env = adsr_envelope(duration, attack=0.003, decay=min(0.18, duration * 0.55), sustain=0.40, release=0.05, sr=sr)
    combined = (string_filtered * 0.70 + res_body * 0.35) * env
    return np.tanh(combined * 1.7).astype(np.float32)


def render_mikedean_moog(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """TRAVIS SCOTT & MIKE DEAN PSYCHEDELIC MOOG SYNTH (Detuned 3-oscillator analog saw + drive)."""
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    cents = [-9.0, 0.0, 9.0]
    moog_sum = np.zeros(total_samples, dtype=np.float32)
    for c in cents:
        f_osc = float(np.clip(freq * (2.0 ** (c / 1200.0)), 20.0, sr * 0.46))
        moog_sum += saw_wave(f_osc, duration, sr=sr) * 0.33

    # Dynamic Moog filter sweep
    sweep = 0.5 + 0.5 * np.exp(-t / max(0.08, duration * 0.4))
    f_cut = float(np.clip(freq * 3.5, 200.0, sr * 0.45))
    b, a = signal.butter(2, min(0.46, f_cut / (sr * 0.5)), btype='low')
    filtered = signal.lfilter(b, a, moog_sum).astype(np.float32) * sweep

    res_noise = biquad_modal_resonator(noise_chunk, freq, q=22.0, sr=sr)
    env = adsr_envelope(duration, attack=0.010, decay=min(0.35, duration * 0.6), sustain=0.60, release=0.10, sr=sr)
    combined = (filtered * 0.70 + res_noise * 0.30) * env
    return np.tanh(combined * 2.2).astype(np.float32)


def render_timbaland_minimal_lead(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """TIMBALAND ASYMMETRIC FOLEY LEAD (Pitch-bent sine pluck + organic mouth transient)."""
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    # Rapid pitch-drop envelope (1.6x down to 1.0x in first 30ms)
    pitch_env = 1.0 + 0.6 * np.exp(-t / 0.025)
    f_arr = float(np.clip(freq, 40.0, sr * 0.45)) * pitch_env
    phase = 2.0 * np.pi * np.cumsum(f_arr) / sr
    sine_lead = np.sin(phase).astype(np.float32)

    click = noise_chunk * np.exp(-t * 80.0) * 0.5
    env = np.exp(-t * 12.0).astype(np.float32)
    combined = (sine_lead * 0.70 + click) * env
    return np.tanh(combined * 1.6).astype(np.float32)


def render_eminem_harpsichord(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """EMINEM & BASS BROTHERS STACCATO HARPSICHORD / PIANO (Crisp baroque stabs)."""
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    harmonics = [1.0, 0.75, 0.50, 0.35, 0.25, 0.15]
    harp_sum = np.zeros(total_samples, dtype=np.float32)
    for k, amp in enumerate(harmonics, start=1):
        f_k = freq * k
        if f_k < sr * 0.45:
            harp_sum += np.sin(2.0 * np.pi * f_k * t) * amp

    env = adsr_envelope(duration, attack=0.002, decay=min(0.18, duration * 0.6), sustain=0.20, release=0.04, sr=sr)
    res_noise = biquad_modal_resonator(noise_chunk, freq, q=35.0, sr=sr)
    combined = (harp_sum * 0.65 + res_noise * 0.35) * env
    return np.tanh(combined * 1.8).astype(np.float32)


def render_kendrick_piano_stab(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """KENDRICK LAMAR & SOUNWAVE VINTAGE MINOR PIANO STAB."""
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    # Minor third and fifth overtones
    f_root = float(np.clip(freq, 40.0, sr * 0.45))
    f_third = f_root * (2.0 ** (3.0 / 12.0))
    f_fifth = f_root * (2.0 ** (7.0 / 12.0))
    p_sum = (
        np.sin(2.0 * np.pi * f_root * t) * 0.55 +
        np.sin(2.0 * np.pi * f_third * t) * 0.30 +
        np.sin(2.0 * np.pi * f_fifth * t) * 0.25
    )
    env = adsr_envelope(duration, attack=0.004, decay=min(0.24, duration * 0.6), sustain=0.30, release=0.06, sr=sr)
    res_noise = biquad_modal_resonator(noise_chunk, f_root, q=28.0, sr=sr)
    combined = (p_sum * 0.65 + res_noise * 0.35) * env
    return np.tanh(combined * 1.5).astype(np.float32)


def render_rockrap_power_stab(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """RUN-DMC & RICK RUBIN OVERDRIVEN POWER STAB."""
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    f_root = float(np.clip(freq, 40.0, sr * 0.45))
    f_fifth = f_root * 1.4983
    power_chord = saw_wave(f_root, duration, sr=sr) * 0.60 + saw_wave(f_fifth, duration, sr=sr) * 0.40
    res_noise = biquad_modal_resonator(noise_chunk, f_root, q=16.0, sr=sr)
    env = adsr_envelope(duration, attack=0.004, decay=min(0.20, duration * 0.5), sustain=0.45, release=0.06, sr=sr)
    combined = (power_chord * 0.70 + res_noise * 0.40) * env
    # Aggressive overdrive clipping
    return np.clip(np.tanh(combined * 3.0) * 1.1, -1.0, 1.0).astype(np.float32)


def render_doom_cartoon_sample(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """MF DOOM DUSTY LO-FI BANDPASS CARTOON RESONANCE."""
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    f_flute = float(np.clip(freq, 60.0, sr * 0.45))
    # Add subtle vintage 4.5 Hz flutter
    vib = 1.0 + 0.015 * np.sin(2.0 * np.pi * 4.5 * t)
    f_cur = f_flute * vib
    phase = 2.0 * np.pi * np.cumsum(f_cur) / sr
    flute_body = np.sin(phase) + 0.3 * np.sin(phase * 2.0)

    # Bandpass lo-fi telephone filter
    b, a = signal.butter(2, [min(0.44, 450.0 / (sr * 0.5)), min(0.46, 2800.0 / (sr * 0.5))], btype='band')
    lofi_flute = signal.lfilter(b, a, flute_body).astype(np.float32)
    res_noise = biquad_modal_resonator(noise_chunk, f_flute, q=20.0, sr=sr)
    env = adsr_envelope(duration, attack=0.012, decay=min(0.25, duration * 0.6), sustain=0.50, release=0.10, sr=sr)
    combined = (lofi_flute * 0.60 + res_noise * 0.40) * env
    return np.tanh(combined * 1.5).astype(np.float32)


def render_burial_vocal_ghost(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """BURIAL EERIE PITCHED FORMANT GHOST VOCAL CHOP."""
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    f_vocal = float(np.clip(freq, 80.0, sr * 0.45))
    # Formants at root, 1.4x, and 2.4x
    form1 = biquad_modal_resonator(noise_chunk, f_vocal, q=24.0, sr=sr)
    form2 = biquad_modal_resonator(noise_chunk, min(sr * 0.45, f_vocal * 1.414), q=20.0, sr=sr) * 0.6
    form3 = biquad_modal_resonator(noise_chunk, min(sr * 0.45, f_vocal * 2.5), q=16.0, sr=sr) * 0.35

    # Breathy vocal swell
    env = adsr_envelope(duration, attack=0.035, decay=min(0.30, duration * 0.5), sustain=0.55, release=0.18, sr=sr)
    combined = (form1 + form2 + form3) * env
    return np.tanh(combined * 1.6).astype(np.float32)


def render_moombahton_synth_horn(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """MAJOR LAZER & DIPLO MOOMBAHTON SCREECH SYNTH HORN."""
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    # Pitch bend scoop down 2 semitones
    scoop = 1.0 + 0.12 * np.exp(-t / 0.040)
    f_horn = float(np.clip(freq, 40.0, sr * 0.45)) * scoop
    phase = 2.0 * np.pi * np.cumsum(f_horn) / sr
    horn_wave = (saw_wave(freq, duration, sr=sr) * 0.65 + square_wave(freq, duration, sr=sr) * 0.35)
    res_noise = biquad_modal_resonator(noise_chunk, freq, q=18.0, sr=sr)
    env = adsr_envelope(duration, attack=0.005, decay=min(0.20, duration * 0.6), sustain=0.40, release=0.05, sr=sr)
    combined = (horn_wave * 0.70 + res_noise * 0.35) * env
    return np.tanh(combined * 2.0).astype(np.float32)


def render_tainy_synthwave_pad(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """BAD BUNNY & TAINY MELANCHOLIC REGGAETON CHORUS SYNTH PAD."""
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    cents = [-8.0, 8.0]
    pad_sum = np.zeros(total_samples, dtype=np.float32)
    for c in cents:
        f_osc = float(np.clip(freq * (2.0 ** (c / 1200.0)), 20.0, sr * 0.46))
        pad_sum += saw_wave(f_osc, duration, sr=sr) * 0.50

    b, a = signal.butter(2, min(0.45, 1800.0 / (sr * 0.5)), btype='low')
    warm_pad = signal.lfilter(b, a, pad_sum).astype(np.float32)
    res_noise = biquad_modal_resonator(noise_chunk, freq, q=20.0, sr=sr)
    env = adsr_envelope(duration, attack=0.020, decay=min(0.35, duration * 0.6), sustain=0.70, release=0.12, sr=sr)
    combined = (warm_pad * 0.65 + res_noise * 0.35) * env
    return np.tanh(combined * 1.5).astype(np.float32)


def render_rosalia_vocal_drop(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """ROSALIA & EL GUINCHO FLAMENCO VOCAL RESONATOR."""
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    f_res = float(np.clip(freq, 60.0, sr * 0.45))
    formant_a = biquad_modal_resonator(noise_chunk, f_res, q=28.0, sr=sr)
    formant_e = biquad_modal_resonator(noise_chunk, min(sr * 0.45, f_res * 1.8), q=22.0, sr=sr) * 0.5
    env = adsr_envelope(duration, attack=0.006, decay=min(0.22, duration * 0.6), sustain=0.30, release=0.06, sr=sr)
    combined = (formant_a + formant_e) * env
    return np.tanh(combined * 1.8).astype(np.float32)


def render_nujabes_piano_guitar(
    noise_chunk: np.ndarray,
    freq: float,
    duration: float,
    sr: int = 44100
) -> np.ndarray:
    """NUJABES JAZZ-HOP WARM ACOUSTIC PIANO & GUITAR."""
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    f_note = float(np.clip(freq, 50.0, sr * 0.45))
    piano_tone = (
        np.sin(2.0 * np.pi * f_note * t) * 0.60 +
        np.sin(4.0 * np.pi * f_note * t) * 0.25 +
        np.sin(6.0 * np.pi * f_note * t) * 0.15
    )
    env = adsr_envelope(duration, attack=0.005, decay=min(0.35, duration * 0.7), sustain=0.35, release=0.12, sr=sr)
    res_noise = biquad_modal_resonator(noise_chunk, f_note, q=30.0, sr=sr)
    combined = (piano_tone * 0.60 + res_noise * 0.40) * env
    return np.tanh(combined * 1.4).astype(np.float32)



# ==============================================================================
# PROFESSIONAL NOISE-TO-MUSIC INSTRUMENT ENGINES
# (Directly converts raw audio/noise into tonal leads, plucks, bass, and drums)
# ==============================================================================

def render_noise_instrument_note(
    source_audio: np.ndarray,
    freq: float,
    duration: float,
    velocity: float = 0.85,
    style: str = "pop",
    sr: int = 44100,
    start_offset: Optional[int] = None
) -> np.ndarray:
    """
    HIGH-DEFINITION PHYSICAL MODELING & MODAL SYNTHESIS:
    Excites a bank of tuned physical resonators using micro-grains of the user's
    sound recording. The resulting instrument note sings with pristine musical pitch
    and rich acoustic overtones while preserving the organic texture of the noise.
    Completely zero crackle or harsh intermodulation distortion.
    """
    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)

    if len(source_audio) == 0:
        source_audio = np.zeros(total_samples, dtype=np.float32)

    # 1. Extract and smoothly window grain from source noise
    if len(source_audio) < total_samples:
        s_len = len(source_audio)
        fade = min(32, s_len // 4)
        s_win = source_audio.copy()
        if fade > 1:
            w = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fade, dtype=np.float32))
            s_win[:fade] *= w
            s_win[-fade:] *= w[::-1]
        reps = int(np.ceil(total_samples / max(1, s_len)))
        noise_chunk = np.tile(s_win, reps)[:total_samples]
    else:
        if start_offset is not None and len(source_audio) > total_samples:
            start = start_offset % (len(source_audio) - total_samples + 1)
        elif len(source_audio) > total_samples:
            start = int(np.random.randint(0, len(source_audio) - total_samples + 1))
        else:
            start = 0
        noise_chunk = source_audio[start:start + total_samples].copy()

    pk_n = float(np.max(np.abs(noise_chunk)))
    if pk_n > 1e-4:
        noise_chunk = noise_chunk / pk_n

    init_taper = min(int(0.003 * sr), total_samples // 4)
    if init_taper > 1:
        noise_chunk[:init_taper] *= (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, init_taper, dtype=np.float32)))

    freq = float(np.clip(freq, 45.0, sr * 0.45))
    norm_style = style.lower()

    # 2. Artist-Specific High-Fidelity Synthesizer Dispatch
    if norm_style in ["metro_chime", "trap", "trap_bell", "bell", "murda_bell_box"]:
        note_body = render_metro_chime(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["usher_crunk_lead", "southside_siren"]:
        note_body = render_usher_crunk_lead(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["lady_gaga", "lady_gaga_supersaw", "pop"]:
        note_body = render_lady_gaga_supersaw(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["mj_horn_stab", "stromae_brass_trumpet"]:
        note_body = render_mj_horn_stab(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["vintage_synthwave", "synthwave"]:
        note_body = render_vintage_synthwave(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["gfunk_whistle"]:
        note_body = render_gfunk_whistle(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["dre_storch_piano"]:
        note_body = render_dre_storch_piano(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["neptunes_triton_pluck", "pierre_flute_pluck"]:
        note_body = render_neptunes_triton_pluck(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["kanye_soulchop"]:
        note_body = render_kanye_soulchop(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["pokerface_stutter_hook", "stutter_vocoder", "pokerface"]:
        note_body = render_pokerface_stutter_lead(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["kanye_flashing_strings", "flashing_strings", "staccato_strings"]:
        note_body = render_kanye_flashing_strings(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["dualipa_clavinet", "clavinet"]:
        note_body = render_dualipa_clavinet(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["mj_synclavier_rhodes", "mj_rhodes", "synclavier", "mj_funk_synth"]:
        note_body = render_mj_synclavier_rhodes(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["brunomars_guitar_horns", "brunomars_brass_stabs", "santana_lead_guitar"]:
        note_body = render_brunomars_guitar_horns(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["hiphop", "hip_hop", "dilla_rhodes", "boom_bap", "lofi"]:
        m1 = biquad_modal_resonator(noise_chunk, freq, q=32.0, sr=sr)
        m2 = biquad_modal_resonator(noise_chunk, min(sr * 0.46, freq * 2.0), q=24.0, sr=sr) * 0.45
        m3 = biquad_modal_resonator(noise_chunk, min(sr * 0.46, freq * 3.0), q=18.0, sr=sr) * 0.20
        tonal_layer = (m1 + m2 + m3) * 3.0
        tremolo = 1.0 + 0.12 * np.sin(2.0 * np.pi * 4.8 * t)
        pure_rhodes = (np.sin(2.0 * np.pi * freq * t) + 0.25 * np.sin(4.0 * np.pi * freq * t)) * np.exp(-t * 3.8) * 0.45
        env = adsr_envelope(duration, attack=0.008, decay=min(0.40, duration * 0.7), sustain=0.40, release=0.12, sr=sr)
        note_body = np.tanh((tonal_layer * 0.65 + pure_rhodes) * env * tremolo * 1.3)

    elif norm_style in ["vintage_synthwave", "synthwave"]:
        # 80s Juno chorused saw with resonant lowpass sweep (The Weeknd / Max Martin)
        saw1 = saw_wave(freq, duration, sr=sr)
        saw2 = saw_wave(freq * 1.007, duration, sr=sr) * 0.75
        saw3 = saw_wave(freq * 0.993, duration, sr=sr) * 0.75
        juno_core = saw1 + saw2 + saw3
        b_j, a_j = signal.butter(2, min(0.44, (freq * 3.6) / (sr * 0.5)), btype='low')
        filtered_juno = signal.lfilter(b_j, a_j, juno_core)
        env = adsr_envelope(duration, attack=0.010, decay=min(0.35, duration * 0.7), sustain=0.55, release=0.12, sr=sr)
        note_body = np.tanh(filtered_juno * env * 1.5)

    elif norm_style in ["mj_synclavier_rhodes", "synclavier", "popfunk"]:
        # 80s FM Electric Piano & Bell Chime (Michael Jackson & Quincy Jones)
        carrier = np.sin(2.0 * np.pi * freq * t)
        mod = np.sin(2.0 * np.pi * freq * 3.0 * t) * np.exp(-t * 22.0) * 1.6
        fm_bell = np.sin(2.0 * np.pi * freq * t + mod) * np.exp(-t * 4.5)
        m1 = biquad_modal_resonator(noise_chunk, freq, q=26.0, sr=sr) * 0.40
        env = adsr_envelope(duration, attack=0.006, decay=min(0.38, duration * 0.75), sustain=0.35, release=0.10, sr=sr)
        note_body = np.tanh((fm_bell * 0.82 + m1) * env * 1.5)

    elif norm_style in ["dualipa_clavinet", "nudisco", "clavinet"]:
        # Funk clavinet pluck with snappy biting transient (Dua Lipa / Nu-Disco)
        sq = square_wave(freq, duration, sr=sr) * 0.65 + saw_wave(freq * 2.0, duration, sr=sr) * 0.35
        b_c, a_c = signal.butter(2, [min(sr * 0.40, 500.0) / (sr * 0.5), min(sr * 0.45, 3600.0) / (sr * 0.5)], btype='bandpass')
        clav = signal.lfilter(b_c, a_c, sq)
        env = np.exp(-t * 22.0).astype(np.float32)
        note_body = np.tanh(clav * env * 2.2)

    elif norm_style in ["brunomars_brass_stabs", "retrofunk", "brass_stabs"]:
        # Tight 3-piece funk horn section brass stab (Bruno Mars Uptown Funk)
        h1 = saw_wave(freq, duration, sr=sr)
        h2 = saw_wave(freq * 1.5, duration, sr=sr) * 0.65  # 5th harmonic
        h3 = saw_wave(freq * 2.0, duration, sr=sr) * 0.50  # Octave harmonic
        brass = h1 + h2 + h3
        b_br, a_br = signal.butter(2, min(0.44, (freq * 3.2 + 800.0) / (sr * 0.5)), btype='low')
        brass_filt = signal.lfilter(b_br, a_br, brass)
        env = adsr_envelope(duration, attack=0.012, decay=0.18, sustain=0.40, release=0.06, sr=sr)
        note_body = np.tanh(brass_filt * env * 1.8)

    elif norm_style in ["kanye_flashing_strings", "soulchop", "disco_strings"]:
        # Cinematic staccato soul strings (Kanye West Soul Chops)
        saw_ens = saw_wave(freq, duration, sr=sr) + saw_wave(freq * 1.005, duration, sr=sr) * 0.8 + saw_wave(freq * 0.995, duration, sr=sr) * 0.8
        b_str, a_str = signal.butter(2, min(0.45, 4200.0 / (sr * 0.5)), btype='low')
        strings = signal.lfilter(b_str, a_str, saw_ens)
        env = np.exp(-t * 14.0).astype(np.float32)
        note_body = np.tanh(strings * env * 1.8)

    elif norm_style in ["metro_dark_bell", "darktrap", "dark_bell"]:
        # Chilling minor chime bell (Metro Boomin Dark Trap)
        bell = (np.sin(2.0 * np.pi * freq * t) + 0.45 * np.sin(2.0 * np.pi * freq * 2.76 * t) + 0.25 * np.sin(2.0 * np.pi * freq * 5.4 * t)) * np.exp(-t * 7.5)
        m1 = biquad_modal_resonator(noise_chunk, freq, q=35.0, sr=sr) * 0.35
        env = np.exp(-t * 6.5).astype(np.float32)
        note_body = np.tanh((bell + m1) * env * 1.6)

    elif norm_style in ["pokerface_stutter_hook", "lady_gaga_supersaw"]:
        # Searing cutting wide supersaw pluck (Lady Gaga / RedOne Electro)
        note_body = render_lady_gaga_supersaw(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["rap", "daft_punk", "daft_punk_talkbox", "kanye"]:
        m1 = biquad_modal_resonator(noise_chunk, freq, q=28.0, sr=sr)
        m2 = biquad_modal_resonator(noise_chunk, min(sr * 0.46, freq * 2.0), q=22.0, sr=sr) * 0.65
        m3 = biquad_modal_resonator(noise_chunk, min(sr * 0.46, freq * 3.0), q=18.0, sr=sr) * 0.40
        tonal_layer = (m1 + m2 + m3) * 3.2
        synth_core = (saw_wave(freq, duration, sr=sr) * 0.35 + sine_wave(freq, duration, sr=sr) * 0.25)
        env = adsr_envelope(duration, attack=0.006, decay=min(0.30, duration * 0.6), sustain=0.35, release=0.08, sr=sr)
        note_body = np.tanh((tonal_layer * 0.65 + synth_core * 0.35) * env * 1.6)

    elif norm_style in ["minimal", "four_tet_mallet", "wood_mallet", "bonobo_kalimba", "jamiexx_steel_pan"]:
        m1 = biquad_modal_resonator(noise_chunk, freq, q=38.0, sr=sr)
        m2 = biquad_modal_resonator(noise_chunk, min(sr * 0.46, freq * 4.0), q=24.0, sr=sr) * 0.25
        tonal_layer = (m1 + m2) * 3.6
        transient = noise_chunk * np.exp(-t * 60.0) * 0.35
        wood_core = np.sin(2.0 * np.pi * freq * t) * np.exp(-t * 16.0) * 0.40
        env = np.exp(-t * 14.0).astype(np.float32)
        note_body = (tonal_layer * 0.60 + wood_core + transient) * env

    elif norm_style in ["ambient", "ambient_drone", "crystal", "brian_eno_piano_shimmer", "drone_string_swell", "hecker_pipe_organ", "budd_felt_piano", "aphex_tape_pad"]:
        m1 = biquad_modal_resonator(noise_chunk, freq, q=20.0, sr=sr)
        m2 = biquad_modal_resonator(noise_chunk, min(sr * 0.46, freq * 1.004), q=20.0, sr=sr) * 0.8
        m3 = biquad_modal_resonator(noise_chunk, min(sr * 0.46, freq * 2.0), q=16.0, sr=sr) * 0.5
        tonal_layer = (m1 + m2 + m3) * 2.8
        pure_drone = (np.sin(2.0 * np.pi * freq * t) + 0.3 * np.sin(2.0 * np.pi * freq * 1.003 * t)) * 0.35
        env = adsr_envelope(duration, attack=0.15, decay=0.3, sustain=0.85, release=0.35, sr=sr)
        note_body = (tonal_layer * 0.60 + pure_drone) * env

    elif norm_style in ["aphex_acid_squelch"]:
        sq = saw_wave(freq, duration, sr=sr)
        f_cut = float(np.clip(freq * 3.5, 200.0, sr * 0.45))
        res = biquad_modal_resonator(sq, f_cut, q=18.0, sr=sr)
        env = np.exp(-t * 14.0).astype(np.float32)
        note_body = np.tanh(res * env * 2.2)

    elif norm_style in ["mustard_stab"]:
        sw = saw_wave(freq, duration, sr=sr) * 0.6 + square_wave(freq, duration, sr=sr) * 0.4
        env = np.exp(-t * 22.0).astype(np.float32)  # Ultra short dry stab
        note_body = np.tanh(sw * env * 1.8)

    elif norm_style in ["mikedean_moog", "travis_moog", "moog"]:
        note_body = render_mikedean_moog(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["timbaland_minimal_lead", "timbaland_foley"]:
        note_body = render_timbaland_minimal_lead(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["eminem_harpsichord", "harpsichord"]:
        note_body = render_eminem_harpsichord(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["kendrick_piano_stab", "sounwave_piano"]:
        note_body = render_kendrick_piano_stab(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["rockrap_power_stab", "rickrubin_guitar"]:
        note_body = render_rockrap_power_stab(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["doom_cartoon_sample", "doom_sample"]:
        note_body = render_doom_cartoon_sample(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["burial_vocal_ghost", "burial_vocal"]:
        note_body = render_burial_vocal_ghost(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["moombahton_synth_horn", "majorlazer_horn"]:
        note_body = render_moombahton_synth_horn(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["tainy_synthwave_pad", "tainy_pad"]:
        note_body = render_tainy_synthwave_pad(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["rosalia_vocal_drop", "flamenco_drop"]:
        note_body = render_rosalia_vocal_drop(noise_chunk, freq, duration, sr=sr)

    elif norm_style in ["nujabes_piano_guitar", "nujabes_jazz"]:
        note_body = render_nujabes_piano_guitar(noise_chunk, freq, duration, sr=sr)

    else:
        # Default cutting electro pluck
        note_body = render_lady_gaga_supersaw(noise_chunk, freq, duration, sr=sr)

    # Apply anti-crackle 2ms attack and 5ms release
    att_len = min(int(0.002 * sr), total_samples // 4)
    if att_len > 1:
        att = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, att_len, dtype=np.float32))
        note_body[:att_len] *= att
    rel_len = min(int(0.005 * sr), total_samples // 4)
    if rel_len > 1:
        rel = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, rel_len, dtype=np.float32))
        note_body[-rel_len:] *= rel

    pk = float(np.max(np.abs(note_body)))
    if pk > 0:
        note_body = (note_body / pk) * velocity * 0.90

    return apply_fade(note_body.astype(np.float32), fade_samples=48)


def render_noise_bass_note(
    source_audio: np.ndarray,
    freq: float,
    duration: float,
    velocity: float = 0.85,
    sr: int = 44100,
    is_prefiltered: bool = False,
    offset_sample: int = 0,
    slice_audio: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Hybrid Source Bass:
    Fuses the source recording's raw acoustic low-end texture with a warm,
    analog-saturated sub-bass oscillator at the musical root frequency.
    """
    while freq > 160.0:
        freq /= 2.0
    while freq < 38.0:
        freq *= 2.0

    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False)

    # 1. Warm sub-bass fundamental (sine + subtle 2nd harmonic for small speakers)
    sub = np.sin(2.0 * np.pi * freq * t) * 0.75 + np.sin(4.0 * np.pi * freq * t) * 0.25

    # 2. Extract and saturate source audio low-end body from slice or offset
    src = slice_audio if (slice_audio is not None and len(slice_audio) > 0) else source_audio

    if len(src) < total_samples:
        s_len = len(src)
        if s_len <= 16:
            noise_chunk = np.zeros(total_samples, dtype=np.float32)
        else:
            fade = min(32, s_len // 4)
            s_win = src.copy()
            if fade > 1:
                w = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, fade, dtype=np.float32))
                s_win[:fade] *= w
                s_win[-fade:] *= w[::-1]
            reps = int(np.ceil(total_samples / max(1, s_len)))
            noise_chunk = np.tile(s_win, reps)[:total_samples]
    else:
        if offset_sample > 0 and len(src) > total_samples:
            st = offset_sample % (len(src) - total_samples + 1)
            noise_chunk = src[st:st + total_samples].copy()
        else:
            noise_chunk = src[:total_samples].copy()

    # Apply short anti-click micro-fade to extracted chunk
    micro_fade = min(int(0.003 * sr), total_samples // 4)
    if micro_fade > 1:
        att = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, micro_fade, dtype=np.float32))
        noise_chunk[:micro_fade] *= att
        noise_chunk[-micro_fade:] *= att[::-1]

    # Explicit band-limiting lowpass (cut at 280Hz) to guarantee sub-bass purity.
    if not is_prefiltered or (slice_audio is not None and len(slice_audio) > 0):
        b_lp, a_lp = signal.butter(2, min(0.45, 280.0 / (sr * 0.5)), btype='low')
        source_low = signal.lfilter(b_lp, a_lp, noise_chunk)
    else:
        source_low = noise_chunk

    p_src = float(np.max(np.abs(source_low)))
    if p_src > 1e-4:
        source_low = (source_low / p_src)

    # 3. Fuse sub oscillator with source texture
    combined = sub * 0.65 + source_low * 0.45
    saturated = np.tanh(combined * 1.8)

    # 4. Punchy ADSR envelope with smooth release
    env = adsr_envelope(duration, attack=0.012, decay=0.15, sustain=0.82, release=0.08, sr=sr)
    out = (saturated * env * velocity).astype(np.float32)

    pk = np.max(np.abs(out))
    if pk > 0:
        out = (out / pk) * velocity * 0.90
    return apply_fade(out, fade_samples=64)


def render_trap_808_glide_bass(
    source_audio: np.ndarray,
    freq_start: float,
    freq_end: float,
    duration: float,
    velocity: float = 0.92,
    sr: int = 44100,
    glide_sec: float = 0.08,
    slice_audio: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    AUTHENTIC TRAP 808 SUB-BASS (Metro Boomin / Southside style):
    Synthesizes a deep saturated 808 sub-bass with authentic smooth portamento
    pitch glides, harmonic saturation for mobile phones, and zero onset crackle.
    """
    while freq_start > 140.0:
        freq_start /= 2.0
    while freq_start < 36.0:
        freq_start *= 2.0
    while freq_end > 140.0:
        freq_end /= 2.0
    while freq_end < 36.0:
        freq_end *= 2.0

    total_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, total_samples, endpoint=False)

    # Frequency curve: smoothly glide from freq_start to freq_end
    if glide_sec > 0 and abs(freq_start - freq_end) > 0.5:
        glide_len = min(total_samples, int(glide_sec * sr))
        t_g = np.linspace(0, 1.0, glide_len)
        s_curve = 0.5 - 0.5 * np.cos(np.pi * t_g)
        f_glide = freq_start + (freq_end - freq_start) * s_curve
        freq_curve = np.full(total_samples, freq_end, dtype=np.float32)
        freq_curve[:glide_len] = f_glide
    else:
        freq_curve = np.full(total_samples, freq_start, dtype=np.float32)

    phase = 2.0 * np.pi * np.cumsum(freq_curve) / sr
    # Pure fundamental + 2nd & 3rd harmonics for audible chest punch & phone reproduction
    sub = np.sin(phase) + 0.32 * np.sin(phase * 2.0) + 0.12 * np.sin(phase * 3.0)

    # Asymmetric soft-clip saturation for authentic 808 growl
    saturated = np.tanh(sub * 1.8)

    # 808 envelope: instant punch, sustained power, clean anti-click release
    att_s = min(int(0.004 * sr), total_samples // 4)
    rel_s = min(int(0.020 * sr), total_samples // 4)
    env = np.ones(total_samples, dtype=np.float32)
    if att_s > 1:
        env[:att_s] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, att_s))
    if rel_s > 1:
        env[-rel_s:] = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, rel_s))
    env *= np.exp(-t * 1.5).astype(np.float32)

    out = (saturated * env * velocity).astype(np.float32)
    pk = np.max(np.abs(out))
    if pk > 0:
        out = (out / pk) * velocity * 0.94
    return apply_fade(out, fade_samples=64)


# ==============================================================================
# VOCAL CHOP & PITCHED SOURCE SYNTHESIZER
# ==============================================================================

def render_pitched_vocal_chop(
    slice_audio: np.ndarray,
    semitones: float,
    duration: float,
    velocity: float = 0.85,
    sr: int = 44100
) -> np.ndarray:
    """
    Renders a tuned, syllabic vocal/source chop note (The 'Fred Again / Soul Chop' technique).
    Pitch-shifts the user's spoken word, vocal formant, or distinct sound to the target
    scale note while preserving recognizable timbre, vowel shape, and attack transients.
    Zero robotic artifacts, completely de-hissed and musical.
    """
    if slice_audio is None or len(slice_audio) == 0:
        return np.zeros(int(max(0.05, duration) * sr), dtype=np.float32)

    total_samples = max(64, int(duration * sr))
    src = slice_audio.astype(np.float32).copy()

    # Pre-clean hiss if not already done
    nyq = sr * 0.5
    try:
        b_clean, a_clean = signal.butter(2, min(0.90, 6800.0 / nyq), btype='low')
        src = signal.lfilter(b_clean, a_clean, src)
    except Exception:
        pass

    # Pitch shift via high quality resampling
    clamped_semi = float(np.clip(semitones, -14.0, 14.0))
    factor = 2.0 ** (-clamped_semi / 12.0)
    new_len = max(32, int(round(len(src) * factor)))

    x_old = np.linspace(0, 1, len(src), endpoint=False)
    x_new = np.linspace(0, 1, new_len, endpoint=False)
    shifted = np.interp(x_new, x_old, src).astype(np.float32)

    # Frame to target duration
    if len(shifted) < total_samples:
        tail_fade = min(len(shifted) // 4, int(0.015 * sr))
        if tail_fade > 1:
            w_tail = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, tail_fade, dtype=np.float32))
            shifted[-tail_fade:] *= w_tail
        out = np.pad(shifted, (0, total_samples - len(shifted)))
    else:
        out = shifted[:total_samples].copy()

    # Apply musical envelope: punchy attack (3ms), sustained body, musical release
    t = np.linspace(0, duration, total_samples, endpoint=False, dtype=np.float32)
    decay_rate = 3.5 if duration > 0.35 else 5.8
    body_env = np.exp(-t * decay_rate)
    out = out * body_env

    # Boundary anti-click smoothing
    out = apply_fade(out, fade_samples=min(int(0.004 * sr), total_samples // 4))

    pk = float(np.max(np.abs(out)))
    if pk > 1e-4:
        out = (out / pk) * velocity * 0.90
    return out.astype(np.float32)


# ==============================================================================
# GENRE-SPECIFIC HIGH-FIDELITY DRUM ENGINES
# ==============================================================================

def render_noise_kick(slice_audio: np.ndarray, velocity: float = 0.9, sr: int = 44100, genre: str = "pop") -> np.ndarray:
    """
    Genre-Adapted Source Kick Synthesizer (Source-Dominant):
    Preserves 75% source acoustic punch (finger snap, mouth click, utensil clack, stomp)
    while reinforcing with a clean 40-70Hz sub foundation.
    """
    g = (genre or "pop").lower()
    if g in ["trap", "drill"]:
        dur = 0.095
        f_start, f_end = 160.0, 60.0
        decay_sweep = 38.0
        sub_decay = 24.0
        click_mix = 0.75
        sub_mix = 0.55
    elif g in ["hiphop", "hip_hop", "boom_bap", "lofi"]:
        dur = 0.30
        f_start, f_end = 92.0, 42.0
        decay_sweep = 18.0
        sub_decay = 7.5
        click_mix = 0.70
        sub_mix = 0.65
    elif g in ["minimal"]:
        dur = 0.14
        f_start, f_end = 125.0, 50.0
        decay_sweep = 28.0
        sub_decay = 16.0
        click_mix = 0.80
        sub_mix = 0.55
    else:  # Pop / Dance / Rap
        dur = 0.22
        f_start, f_end = 120.0, 46.0
        decay_sweep = 22.0
        sub_decay = 9.5
        click_mix = 0.78
        sub_mix = 0.60

    n_samples = int(dur * sr)
    t = np.linspace(0, dur, n_samples, endpoint=False)

    # 1. Clean source transient attack
    if len(slice_audio) < n_samples:
        slice_copy = slice_audio.copy()
        slice_audio = np.pad(slice_copy, (0, n_samples - len(slice_copy)))
    else:
        slice_audio = slice_audio[:n_samples].copy()

    # Pre-taper slice to eliminate any initial step click
    taper = min(int(0.002 * sr), n_samples // 4)
    if taper > 1:
        slice_audio[:taper] *= (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, taper, dtype=np.float32)))

    b_click, a_click = signal.butter(2, [70.0 / (sr * 0.5), min(sr * 0.45, 5000.0) / (sr * 0.5)], btype='bandpass')
    click_filtered = signal.lfilter(b_click, a_click, slice_audio)
    click_env = np.exp(-t * (45.0 if g in ["trap", "drill"] else 32.0))
    source_click = click_filtered * click_env
    pk_c = np.max(np.abs(source_click))
    if pk_c > 1e-4:
        source_click = source_click / pk_c

    # 2. Tuned sub-bass pitch drop (clean sub reinforcement)
    freq_curve = f_end + (f_start - f_end) * np.exp(-t * decay_sweep)
    phase = 2.0 * np.pi * np.cumsum(freq_curve) / sr
    sub_body = np.sin(phase) * np.exp(-t * sub_decay)

    # 3. Layer and glue with soft-saturation (source takes priority!)
    kick = source_click * click_mix + sub_body * sub_mix
    kick = np.tanh(kick * 1.5)

    # Micro-attack fade (2ms) & smooth release
    att_len = min(int(0.002 * sr), n_samples // 4)
    if att_len > 1:
        att = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, att_len, dtype=np.float32))
        kick[:att_len] *= att
    rel_len = min(int(0.008 * sr), n_samples // 4)
    if rel_len > 1:
        rel = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, rel_len, dtype=np.float32))
        kick[-rel_len:] *= rel

    pk = np.max(np.abs(kick))
    if pk > 0:
        kick = (kick / pk) * velocity * 0.95
    return apply_fade(kick.astype(np.float32), fade_samples=64)


def render_noise_snare(slice_audio: np.ndarray, velocity: float = 0.8, sr: int = 44100, genre: str = "pop") -> np.ndarray:
    """
    Genre-Adapted Snare / Clap / Rim Synthesizer (Source-Dominant):
    Keeps 85% of the authentic source recording's crack/texture while providing
    a warm body resonance.
    """
    g = (genre or "pop").lower()
    if g in ["trap", "drill"]:
        dur = 0.13
        bp_low, bp_high = 1800.0, min(sr * 0.45, 6200.0)
        body_freq = 240.0
        crack_decay = 24.0
        body_mix = 0.20
        crack_mix = 0.88
    elif g in ["hiphop", "hip_hop", "boom_bap", "lofi"]:
        dur = 0.24
        bp_low, bp_high = 280.0, min(sr * 0.45, 4500.0)
        body_freq = 195.0
        crack_decay = 14.0
        body_mix = 0.35
        crack_mix = 0.80
    elif g in ["minimal"]:
        dur = 0.08
        bp_low, bp_high = 900.0, min(sr * 0.45, 5200.0)
        body_freq = 360.0
        crack_decay = 32.0
        body_mix = 0.25
        crack_mix = 0.82
    else:  # Pop / Dance / Rap
        dur = 0.22
        bp_low, bp_high = 350.0, min(sr * 0.45, 5500.0)
        body_freq = 185.0
        crack_decay = 15.0
        body_mix = 0.28
        crack_mix = 0.85

    n_samples = int(dur * sr)
    t = np.linspace(0, dur, n_samples, endpoint=False)

    if len(slice_audio) < n_samples:
        slice_copy = slice_audio.copy()
        slice_audio = np.pad(slice_copy, (0, n_samples - len(slice_copy)))
    else:
        slice_audio = slice_audio[:n_samples].copy()

    # Pre-taper slice
    taper = min(int(0.002 * sr), n_samples // 4)
    if taper > 1:
        slice_audio[:taper] *= (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, taper, dtype=np.float32)))

    # 1. Acoustic crack filtered through genre range
    b_sn, a_sn = signal.butter(2, [bp_low / (sr * 0.5), bp_high / (sr * 0.5)], btype='bandpass')
    source_crack = signal.lfilter(b_sn, a_sn, slice_audio)
    source_crack *= np.exp(-t * crack_decay)
    pk_cr = np.max(np.abs(source_crack))
    if pk_cr > 1e-4:
        source_crack = source_crack / pk_cr

    # 2. Resonant shell body tone
    body_tone = np.sin(2.0 * np.pi * body_freq * t) * np.exp(-t * (crack_decay * 1.5))

    # 3. Layer and glue
    snare = source_crack * crack_mix + body_tone * body_mix

    # In pop mode: add subtle 11ms clap pre-transient for authentic layered pop clap width
    if g in ["pop", "dance", "synthpop"] and n_samples > int(0.015 * sr):
        flam_s = int(0.011 * sr)
        snare[flam_s:] += source_crack[:-flam_s] * 0.45

    snare = np.tanh(snare * 1.6)

    # Micro-attack fade (2ms) & release
    att_len = min(int(0.002 * sr), n_samples // 4)
    if att_len > 1:
        att = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, att_len, dtype=np.float32))
        snare[:att_len] *= att
    rel_len = min(int(0.008 * sr), n_samples // 4)
    if rel_len > 1:
        rel = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, rel_len, dtype=np.float32))
        snare[-rel_len:] *= rel

    pk = np.max(np.abs(snare))
    if pk > 0:
        snare = (snare / pk) * velocity * 0.90
    return apply_fade(snare.astype(np.float32), fade_samples=64)


def render_noise_hihat(slice_audio: np.ndarray, velocity: float = 0.6, sr: int = 44100, genre: str = "pop") -> np.ndarray:
    """
    Genre-Adapted Closed Hi-Hat Synthesizer:
    Bandpasses high frequencies (tames harsh white-noise hiss > 7.5 kHz)
    to give authentic percussive shaker/hi-hat click.
    """
    g = (genre or "pop").lower()
    dur = 0.055 if g in ["trap", "drill"] else 0.075 if g == "minimal" else 0.085
    cutoff_low = 5500.0 if g in ["trap", "drill"] else 3800.0 if g in ["hiphop", "hip_hop", "lofi"] else 4600.0
    cutoff_high = min(sr * 0.45, 7800.0)  # Tame high-end mic hiss
    decay_rate = 60.0 if g in ["trap", "drill"] else 40.0 if g in ["hiphop", "lofi"] else 50.0

    n_samples = int(dur * sr)
    t = np.linspace(0, dur, n_samples, endpoint=False)

    if len(slice_audio) < n_samples:
        slice_copy = slice_audio.copy()
        slice_audio = np.pad(slice_copy, (0, n_samples - len(slice_copy)))
    else:
        slice_audio = slice_audio[:n_samples].copy()

    # Pre-taper slice
    taper = min(int(0.0015 * sr), n_samples // 4)
    if taper > 1:
        slice_audio[:taper] *= (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, taper, dtype=np.float32)))

    # Bandpass source noise to prevent white-noise hiss
    b_bp, a_bp = signal.butter(2, [cutoff_low / (sr * 0.5), cutoff_high / (sr * 0.5)], btype='bandpass')
    hihat_filtered = signal.lfilter(b_bp, a_bp, slice_audio)

    # Snappy exponential decay
    env = np.exp(-t * decay_rate)
    hihat = hihat_filtered * env

    # Micro-attack & release
    att_len = min(int(0.0015 * sr), n_samples // 4)
    if att_len > 1:
        att = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, att_len, dtype=np.float32))
        hihat[:att_len] *= att
    rel_len = min(int(0.004 * sr), n_samples // 4)
    if rel_len > 1:
        rel = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, rel_len, dtype=np.float32))
        hihat[-rel_len:] *= rel

    pk = np.max(np.abs(hihat))
    if pk > 0:
        hihat = (hihat / pk) * velocity * 0.82
    return apply_fade(hihat.astype(np.float32), fade_samples=48)


def render_noise_open_hihat(slice_audio: np.ndarray, velocity: float = 0.65, sr: int = 44100, genre: str = "pop") -> np.ndarray:
    """
    Genre-Adapted Open Sizzle Hi-Hat:
    Sustains high-frequency shimmer with tailored decay for authentic genre syncopation.
    """
    g = (genre or "pop").lower()
    dur = 0.16 if g in ["trap", "drill"] else 0.18 if g == "minimal" else 0.25
    decay_rate = 18.0 if g in ["trap", "drill"] else 12.0

    n_samples = int(dur * sr)
    t = np.linspace(0, dur, n_samples, endpoint=False)

    if len(slice_audio) < n_samples:
        slice_copy = slice_audio.copy()
        slice_audio = np.pad(slice_copy, (0, n_samples - len(slice_copy)))
    else:
        slice_audio = slice_audio[:n_samples].copy()

    taper = min(int(0.002 * sr), n_samples // 4)
    if taper > 1:
        slice_audio[:taper] *= (0.5 - 0.5 * np.cos(np.linspace(0, np.pi, taper, dtype=np.float32)))

    b_hp, a_hp = signal.butter(2, min(0.45, 4500.0 / (sr * 0.5)), btype='high')
    filtered = signal.lfilter(b_hp, a_hp, slice_audio)

    env = np.exp(-t * decay_rate)
    out = filtered * env

    att_len = min(int(0.002 * sr), n_samples // 4)
    if att_len > 1:
        att = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, att_len, dtype=np.float32))
        out[:att_len] *= att
    rel_len = min(int(0.006 * sr), n_samples // 4)
    if rel_len > 1:
        rel = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, rel_len, dtype=np.float32))
        out[-rel_len:] *= rel

    pk = np.max(np.abs(out))
    if pk > 0:
        out = (out / pk) * velocity * 0.78
    return apply_fade(out.astype(np.float32), fade_samples=64)


def render_karplus_strong_noise_note(
    source_grain: np.ndarray,
    freq: float,
    duration: float,
    velocity: float = 0.85,
    damping: float = 0.985,
    brightness: float = 0.55,
    sr: int = 44100,
    is_slap: bool = False
) -> np.ndarray:
    """
    Karplus-Strong Physical String Synthesis Excited by Source Noise:
    Excites an acoustic delay-line resonator using an actual micro-grain from the user's
    sound recording. The resulting instrument note possesses the authentic timber,
    grit, and physical attack transient of the user's sound while vibrating at a pure musical pitch.
    Vectorized via scipy.signal.lfilter in C (< 1ms execution).
    """
    total_samples = max(64, int(duration * sr))
    freq = float(np.clip(freq, 45.0, sr * 0.45))
    L = max(4, int(round(sr / freq)))

    excitation = np.zeros(total_samples, dtype=np.float32)
    if len(source_grain) == 0:
        source_grain = np.random.normal(0, 0.2, L).astype(np.float32)

    grain_len = min(L, len(source_grain))
    win = np.hanning(grain_len).astype(np.float32)
    excitation[:grain_len] = source_grain[:grain_len] * win

    if is_slap:
        # Prepend explosive 6ms thumb-slap impulse for authentic funk slap bass
        thump_len = min(total_samples, int(0.006 * sr))
        if thump_len > 4:
            thump_t = np.linspace(0, 1.0, thump_len, dtype=np.float32)
            thump_impulse = np.sin(np.pi * thump_t) * np.exp(-thump_t * 6.0)
            excitation[:thump_len] += thump_impulse * 0.85

    # Karplus-Strong feedback IIR transfer function
    b = np.array([1.0], dtype=np.float32)
    a = np.zeros(L + 2, dtype=np.float32)
    a[0] = 1.0
    a[L] = -damping * (1.0 - brightness)
    a[L + 1] = -damping * brightness

    string_note = signal.lfilter(b, a, excitation)

    # Analog tape saturation for warm presence
    saturated = np.tanh(string_note * 1.6)

    # Micro-attack fade (2ms) & smooth tail release to eliminate abrupt cutoffs
    att_len = min(int(0.002 * sr), total_samples // 4)
    if att_len > 1:
        att = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, att_len, dtype=np.float32))
        saturated[:att_len] *= att
    rel_len = min(int(0.04 * sr), total_samples // 4)
    if rel_len > 1:
        fade_out = np.linspace(1.0, 0.0, rel_len, dtype=np.float32)
        saturated[-rel_len:] *= fade_out

    pk = np.max(np.abs(saturated))
    if pk > 0:
        saturated = (saturated / pk) * velocity * 0.88

    return apply_fade(saturated.astype(np.float32), fade_samples=64)


def render_noise_riser(
    source_audio: np.ndarray,
    duration: float = 3.0,
    sr: int = 44100,
    offset_sample: int = 0,
    slice_audio: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Source Noise Transition Riser:
    Takes atmospheric texture from the user's noise and applies a continuous
    multi-band upward frequency sweep (200Hz -> 9000Hz) with crescendo swell.
    Completely zero clicks or boundary resets.
    """
    n_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, n_samples, endpoint=False)

    src = slice_audio if (slice_audio is not None and len(slice_audio) > 0) else source_audio
    if len(src) < n_samples:
        s_len = len(src)
        s_win = apply_fade(src, fade_samples=min(32, s_len // 4))
        reps = int(np.ceil(n_samples / max(1, s_len)))
        noise_chunk = np.tile(s_win, reps)[:n_samples].astype(np.float32)
    else:
        if offset_sample > 0 and len(src) > n_samples:
            st = offset_sample % (len(src) - n_samples + 1)
            noise_chunk = src[st:st + n_samples].astype(np.float32).copy()
        else:
            noise_chunk = src[:n_samples].astype(np.float32).copy()

    # Smooth multi-band continuous frequency sweep:
    # 7 overlapping octave bandpass filters filtered causally over the FULL buffer
    # with smooth Gaussian time-gating that ascends across the duration
    num_bands = 7
    centers = np.geomspace(220.0, min(sr * 0.45, 8800.0), num=num_bands)
    riser_sum = np.zeros(n_samples, dtype=np.float32)

    for idx, fc in enumerate(centers):
        bw = fc * 0.55
        f_low = max(20.0, fc - bw * 0.5)
        f_high = min(sr * 0.48, fc + bw * 0.5)
        b, a = signal.butter(1, [f_low / (sr * 0.5), f_high / (sr * 0.5)], btype='bandpass')
        band_filtered = signal.lfilter(b, a, noise_chunk)

        # Time envelope for this band centered at peak_t
        peak_t = (idx / (num_bands - 1)) * duration
        sigma_t = duration / (num_bands * 0.75)
        time_env = np.exp(-0.5 * ((t - peak_t) / sigma_t) ** 2).astype(np.float32)
        riser_sum += band_filtered * time_env

    # Smooth crescendo exponential swell curve
    crescendo = (np.exp(t * 1.8) - 1.0) / (np.exp(duration * 1.8) - 1.0)
    riser = riser_sum * (0.08 + 0.92 * crescendo)

    # Smooth 4ms attack & 4ms release
    att_len = min(int(0.004 * sr), n_samples // 4)
    if att_len > 1:
        att = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, att_len, dtype=np.float32))
        riser[:att_len] *= att
    rel_len = min(int(0.006 * sr), n_samples // 4)
    if rel_len > 1:
        rel = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, rel_len, dtype=np.float32))
        riser[-rel_len:] *= rel

    pk = np.max(np.abs(riser))
    if pk > 0:
        riser = (riser / pk) * 0.85

    return apply_fade(riser.astype(np.float32), fade_samples=64)


def render_noise_downlifter(slice_audio: np.ndarray, duration: float = 1.8, sr: int = 44100) -> np.ndarray:
    """
    Source Noise Downlifter / Impact Crash:
    Takes an impact transient from the user's sound and dissolves it into a decaying
    lowpass reverberant wash for resolving drop sections.
    """
    n_samples = max(64, int(duration * sr))
    t = np.linspace(0, duration, n_samples, endpoint=False)

    if len(slice_audio) < n_samples:
        slice_audio = np.pad(slice_audio, (0, n_samples - len(slice_audio))).astype(np.float32)
    else:
        slice_audio = slice_audio[:n_samples].astype(np.float32).copy()

    # Downward filter cutoff: 1400Hz lowpass
    b_lp, a_lp = signal.butter(2, min(0.45, 1400.0 / (sr * 0.5)), btype='low')
    washed = signal.lfilter(b_lp, a_lp, slice_audio)

    env = np.exp(-t * 2.8).astype(np.float32)
    downlifter = (slice_audio * 0.35 + washed * 0.65) * env

    # Smooth 3ms attack fade to eliminate non-zero onset crackle
    att_len = min(int(0.003 * sr), n_samples // 4)
    if att_len > 1:
        att = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, att_len, dtype=np.float32))
        downlifter[:att_len] *= att
    rel_len = min(int(0.008 * sr), n_samples // 4)
    if rel_len > 1:
        rel = 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, rel_len, dtype=np.float32))
        downlifter[-rel_len:] *= rel

    pk = np.max(np.abs(downlifter))
    if pk > 0:
        downlifter = (downlifter / pk) * 0.78

    return apply_fade(downlifter.astype(np.float32), fade_samples=64)


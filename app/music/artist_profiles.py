"""
Iconic Artist Style Profiles Registry for TheUnnecessaryFM
Defines authentic production archetypes across 7 genres with exact BPM ranges,
musical scales, drum groove types, micro-timing humanization, bass architectures,
and signature synthesizer/resonator designs.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from ..utils.random import SeededRNG


@dataclass
class ArtistProfile:
    id: str
    name: str
    track_title_hint: str
    genre: str  # "pop", "trap", "hiphop", "rap", "minimal", "rhythmic", "none"
    bpm_default: float
    bpm_min: float
    bpm_max: float
    preferred_scales: List[str]
    progression_pool: List[List[int]]  # Scale degrees, e.g. [[1, 1, 4, 5], [1, 7, 6, 5]]
    groove_type: str
    lead_style: str
    bass_style: str  # "808_glide", "karplus_bass", "karplus_slap", "saw_pluck", "sub_octave_pulse", "horn_punctuation", "rhodes_bass", "warm_sine", "synth_sub", "ambient_drone"
    humanize_timing_ms: float = 0.0
    lead_reverb: Tuple[float, float] = (0.65, 0.20)  # (room_size, wet_level)
    lead_delay: Tuple[float, float, float] = (0.5, 0.25, 0.20)  # (division, feedback, mix)
    chord_q: float = 20.0
    chord_reverb: Tuple[float, float] = (0.65, 0.20)
    bed_gain_mul: float = 0.65
    melody_mix: float = 0.95
    chord_mix: float = 0.85
    bass_mix: float = 1.00
    special_flags: Dict[str, bool] = field(default_factory=dict)
    display_name: str = ""
    vibe: str = ""
    arrangement_flow: str = "standard_cinematic"
    intro_lead_style: str = ""

    def __post_init__(self):
        if not self.display_name or not self.vibe:
            meta = STYLE_DISPLAY_METADATA.get(self.id, (self.name, self.track_title_hint))
            if not self.display_name:
                self.display_name = meta[0]
            if not self.vibe:
                self.vibe = meta[1]

        if not self.arrangement_flow or self.arrangement_flow == "standard_cinematic":
            if self.id in FLOW_ASSIGNMENTS:
                self.arrangement_flow = FLOW_ASSIGNMENTS[self.id][0]
                if not self.intro_lead_style:
                    self.intro_lead_style = FLOW_ASSIGNMENTS[self.id][1]


FLOW_ASSIGNMENTS: Dict[str, Tuple[str, str]] = {
    "ladygaga_redone_electro": ("hook_first_explosion", "pokerface_stutter_hook"),
    "mj_quincy_popfunk": ("drums_first_build", "mj_synclavier_rhodes"),
    "brunomars_retrofunk": ("funk_vamp_drop", "brunomars_brass_stabs"),
    "kanye_soulchop": ("staccato_strings_drop", "kanye_flashing_strings"),
    "weeknd_maxmartin_synthwave": ("synthwave_driving_drop", "vintage_synthwave"),
    "drdre_scottstorch_gfunk": ("piano_whistle_drop", "dre_storch_piano"),
    "dualipa_nudisco": ("disco_pump_build", "dualipa_clavinet"),
    "metroboomin_darktrap": ("dark_cinematic_drop", "metro_dark_bell"),
}


# Client-Facing Aesthetic Sonic Archetype Names & Vibes
STYLE_DISPLAY_METADATA: Dict[str, Tuple[str, str]] = {
    # Pop & Nu-Disco
    "ladygaga_redone_electro": ("Electro-Pop Supersaw", "Driving four-on-the-floor electro with wide supersaws"),
    "usher_liljon_crunk": ("Crunk Club Siren Riff", "Aggressive siren synth with heavy 808 sub hits"),
    "mj_quincy_popfunk": ("80s Pop Synth Ostinato", "Walking 8th ostinato bass & sparkling FM electric piano"),
    "weeknd_maxmartin_synthwave": ("Neon 80s Synthwave", "Arpeggiated driving pulse with lush Juno chorus leads"),
    "dualipa_nudisco": ("Nu-Disco Club Pump", "16th-note root-octave disco pump & percussive clavinet"),
    "brunomars_retrofunk": ("Retro Uptown Brass Funk", "Tight 3-piece horn stabs & syncopated slap bass"),

    # Trap & Drill
    "metroboomin_darktrap": ("Dark Cinematic Minor Trap", "Chilling piano chords with heavy sliding 808 subs"),
    "southside_808mafia": ("Hard Drill Distortion", "Aggressive brass stabs & saturated sliding 808 glides"),
    "travis_mikedean": ("Psychedelic Moog Odyssey", "Warm soaring Moog leads & distorted low-end distortion"),
    "pierre_bourne": ("8-Bit Playful Chime Trap", "Airy melodic bell plucks & bouncy sub rhythm"),
    "murda_beatz": ("Radio Trap Melodics", "Bright acoustic plucks with punchy rolling hats"),
    "djmustard_ratchet": ("West Coast Ratchet Chants", "Minimal staccato piano plinks with snappy claps"),

    # Hip-Hop & Lo-Fi
    "drdre_scottstorch_gfunk": ("West Coast G-Funk Lead", "Soaring high sine whistle & staccato electric piano"),
    "kanye_soulchop": ("Vintage Soul Sample-Chop", "Warm pitched vocal chops & punchy acoustic boom-bap"),
    "timbaland_percussive": ("Percussive Beatbox Foley", "Organic foley mouth clicks & syncopated groove"),
    "neptunes_minimalfunk": ("Dry Minimal Space Funk", "Sharp dry Triton guitar plucks & four-count start"),
    "j_dilla_lofi": ("Swung MPC Vinyl Lo-Fi", "Dusty unquantized Rhodes keys & lazy swung snare"),
    "nujabes_jazzhop": ("Atmospheric Jazzhop Chords", "Warm jazz piano chords, flute flutter & vinyl dust"),

    # Rap & Electronic Bounce
    "daftpunk_frenchtouch": ("French Touch Filter House", "Resonant low-pass sweeps & funky vocoder leads"),
    "eminem_bassbrothers": ("Detroit Bounce Harpsichord", "Staccato minor harpsichord plink & punchy bassline"),
    "kendrick_sounwave": ("Compton Cinematic Stabs", "Dark reverse piano & heavy dynamic rhythm"),
    "run_dmc_rickrubin": ("80s Rock-Rap Power Chords", "Overdriven power guitar stabs & 808 boom"),
    "mf_doom_villain": ("Vintage Comic Boom-Bap", "Dusty nostalgic cartoon horns & rugged drums"),

    # Minimal & Atmospheric
    "four_tet_textural": ("Organic Textural Micro-House", "Granular bell chimes & intricate organic clicks"),
    "burial_futuregarage": ("Pitched Ghost Vocal Garage", "Vinyl crackle, eerie formant chops & 2-step shuffle"),
    "aphex_twin_braindance": ("Braindance Acid Modular", "Squelchy 303 acid resonant sweeps & micro-edits"),
    "jamie_xx_ukbass": ("UK Bass & Steel Pan Echoes", "Airy steel pans, warm sub swell & spacious delays"),
    "bonobo_organic": ("Global Organic Down-Tempo", "Woodwind acoustics, warm kalimba & lush pads"),

    # Rhythmic & Latin
    "major_lazer_moombahton": ("Moombahton Screech Horns", "Pitch-scooping dancehall horns & 110 BPM dembow"),
    "badbunny_tainy": ("Futuristic Reggaeton Dembow", "Melancholic chorus synth pads & syncopated perreo"),
    "stromae_electrodance": ("European Melancholic Dance", "Punchy euro electro groove & introspective melody"),
    "rosalia_el_guincho": ("Modern Flamenco Vocal Drop", "Staccato flamenco vocal resonance & handclaps"),
    "santana_latinrock": ("Latin Rock Guitar & Congas", "Sustained melodic guitar leads & energetic congas"),

    # Ambient Drone & Meditation
    "brian_eno_generative": ("Generative Shimmer Ambient", "Infinite evolving granular drone & crystalline shimmer"),
    "stars_of_the_lid": ("Harmonic Drone Symphony", "Slow multi-layer analog strings & deep meditative wash"),
    "tim_hecker_frost": ("Digital Frost Texture", "Granular acoustic decay & frozen spectral resonance"),
    "harold_budd_softpiano": ("Felt Piano Reverb Wash", "Muted soft-pedal piano notes in infinite reverberation"),
    "aphex_saw2_dark": ("Deep Subterranean Drone", "Dark cavernous low rumble & hypnotic metallic pulse"),
}


# ==============================================================================
# ARTIST PROFILES REPOSITORY (38 LEGENDARY PROFILES ACROSS 7 GENRES)
# ==============================================================================

ARTIST_PROFILES: Dict[str, ArtistProfile] = {
    # ── 1. GENRE: POP ─────────────────────────────────────────────────────────
    "ladygaga_redone_electro": ArtistProfile(
        id="ladygaga_redone_electro",
        name="Lady Gaga & RedOne (Electro-Pop)",
        track_title_hint="Poker Face / Bad Romance",
        genre="pop",
        bpm_default=124.0,
        bpm_min=118.0,
        bpm_max=126.0,
        preferred_scales=["harmonic_minor", "natural_minor"],
        progression_pool=[[6, 4, 1, 5], [1, 6, 3, 7]],
        groove_type="pop_four_floor",
        lead_style="lady_gaga_supersaw",
        bass_style="saw_pluck",
        humanize_timing_ms=0.0,
        lead_reverb=(0.70, 0.24),
        lead_delay=(0.5, 0.28, 0.24),  # 8th-note stereo ping-pong bounce
        chord_q=16.0,
        chord_reverb=(0.65, 0.20),
        bed_gain_mul=0.68,
        melody_mix=0.98,
        chord_mix=0.88,
        bass_mix=0.98,
        special_flags={"euro_pop_hat": True, "classic_vocal_fusion": True}
    ),
    "usher_liljon_crunk": ArtistProfile(
        id="usher_liljon_crunk",
        name="Usher & Lil Jon (Crunk Club)",
        track_title_hint="Yeah! Club Siren Riff",
        genre="pop",
        bpm_default=105.0,
        bpm_min=100.0,
        bpm_max=108.0,
        preferred_scales=["natural_minor", "dorian"],
        progression_pool=[[1, 1, 4, 5], [1, 7, 6, 5]],
        groove_type="crunk",
        lead_style="usher_crunk_lead",
        bass_style="808_glide",
        humanize_timing_ms=0.0,  # Crunk is rigid, no swing
        lead_reverb=(0.35, 0.10),  # Dry upfront crunk mix
        lead_delay=(0.5, 0.15, 0.12),
        chord_q=18.0,
        chord_reverb=(0.40, 0.12),
        bed_gain_mul=0.60,
        melody_mix=1.12,  # Loud central-forward lead
        chord_mix=0.80,
        bass_mix=1.15,  # Sub-heavy 808
        special_flags={"crunk_rigid": True}
    ),
    "mj_quincy_popfunk": ArtistProfile(
        id="mj_quincy_popfunk",
        name="Michael Jackson & Quincy Jones (Pop Funk)",
        track_title_hint="Billie Jean / Thriller Pocket",
        genre="pop",
        bpm_default=118.0,
        bpm_min=116.0,
        bpm_max=120.0,
        preferred_scales=["dorian", "natural_minor"],
        progression_pool=[[1, 4, 1, 4], [1, 7, 4, 5], [1, 6, 7, 1]],
        groove_type="funk_pocket",
        lead_style="mj_synclavier_rhodes",
        bass_style="billie_jean_ostinato",
        humanize_timing_ms=0.0,  # Tight, unswung quantized pop groove
        lead_reverb=(0.40, 0.14),
        lead_delay=(0.5, 0.18, 0.14),
        chord_q=20.0,
        chord_reverb=(0.55, 0.16),
        bed_gain_mul=0.55,
        melody_mix=0.98,
        chord_mix=0.82,
        bass_mix=1.06,
        special_flags={"tight_pocket": True}
    ),
    "weeknd_maxmartin_synthwave": ArtistProfile(
        id="weeknd_maxmartin_synthwave",
        name="The Weeknd & Max Martin (80s Synthwave)",
        track_title_hint="Blinding Lights Arp",
        genre="pop",
        bpm_default=170.0,
        bpm_min=168.0,
        bpm_max=172.0,
        preferred_scales=["natural_minor"],
        progression_pool=[[1, 6, 7, 3], [1, 7, 6, 7], [6, 4, 1, 5]],
        groove_type="synthwave_driving",
        lead_style="vintage_synthwave",
        bass_style="sub_octave_pulse",
        humanize_timing_ms=0.0,
        lead_reverb=(0.82, 0.32),  # 80s spacious hall reverb
        lead_delay=(0.5, 0.30, 0.22),
        chord_q=22.0,
        chord_reverb=(0.75, 0.28),
        bed_gain_mul=0.62,
        melody_mix=0.96,
        chord_mix=0.86,
        bass_mix=0.96,
        special_flags={"gated_snare": True}
    ),
    "dualipa_nudisco": ArtistProfile(
        id="dualipa_nudisco",
        name="Dua Lipa (Nu-Disco)",
        track_title_hint="Don't Start Now / Levitating",
        genre="pop",
        bpm_default=124.0,
        bpm_min=122.0,
        bpm_max=126.0,
        preferred_scales=["natural_minor", "dorian", "harmonic_minor"],
        progression_pool=[[1, 7, 6, 7], [6, 4, 1, 5], [1, 4, 6, 5], [1, 6, 3, 7]],
        groove_type="disco_boots_cats",
        lead_style="dualipa_clavinet",
        bass_style="disco_octave_pump",
        humanize_timing_ms=0.0,  # Rigid quantized club disco timing
        lead_reverb=(0.50, 0.16),  # Tight snappy room
        lead_delay=(0.5, 0.22, 0.18),
        chord_q=18.0,
        chord_reverb=(0.55, 0.16),
        bed_gain_mul=0.55,
        melody_mix=0.96,
        chord_mix=0.88,
        bass_mix=1.12,  # Heavy driving disco bass
        special_flags={"boots_and_cats": True, "disco_octaves": True}
    ),
    "brunomars_retrofunk": ArtistProfile(
        id="brunomars_retrofunk",
        name="Bruno Mars (Retro Funk & Soul)",
        track_title_hint="24K Magic / Uptown Funk",
        genre="pop",
        bpm_default=116.0,
        bpm_min=114.0,
        bpm_max=118.0,
        preferred_scales=["dorian", "blues", "mixolydian"],
        progression_pool=[[1, 4, 1, 4], [1, 7, 4, 5], [1, 5, 4, 1]],
        groove_type="live_funk_swung",
        lead_style="brunomars_brass_stabs",
        bass_style="karplus_slap",
        humanize_timing_ms=8.0,  # Key differentiator: +/-8ms live funk kit jitter!
        lead_reverb=(0.65, 0.22),
        lead_delay=(0.5, 0.20, 0.16),
        chord_q=22.0,
        chord_reverb=(0.65, 0.22),
        bed_gain_mul=0.62,
        melody_mix=1.05,  # Powerful central horn section
        chord_mix=0.82,
        bass_mix=1.05,
        special_flags={"analog_saturation": True, "live_jitter": True, "funk_slap": True}
    ),


    # ── 2. GENRE: TRAP ────────────────────────────────────────────────────────
    "metroboomin_darktrap": ArtistProfile(
        id="metroboomin_darktrap",
        name="Metro Boomin (Dark Cinematic Trap)",
        track_title_hint="Creepin' / No Heart",
        genre="trap",
        bpm_default=140.0,
        bpm_min=132.0,
        bpm_max=145.0,
        preferred_scales=["natural_minor", "harmonic_minor"],
        progression_pool=[[1, 6, 7, 1], [1, 3, 6, 7], [1, 1, 6, 6]],
        groove_type="metro_halftime",
        lead_style="metro_chime",  # Premium inharmonic bell with reverse tail
        bass_style="808_glide",
        humanize_timing_ms=0.0,
        lead_reverb=(0.92, 0.38),  # Long dark cavernous reverb on chime tail
        lead_delay=(0.75, 0.40, 0.32),
        chord_q=26.0,
        chord_reverb=(0.80, 0.30),
        bed_gain_mul=0.55,
        melody_mix=0.94,
        chord_mix=0.80,
        bass_mix=1.22,  # Heavy sub-bass
        special_flags={"reverse_tail": True, "negative_space": True}
    ),
    "southside_808mafia": ArtistProfile(
        id="southside_808mafia",
        name="Southside & 808 Mafia (Hard Drill Trap)",
        track_title_hint="Stick Talk / Mask Off",
        genre="trap",
        bpm_default=142.0,
        bpm_min=136.0,
        bpm_max=146.0,
        preferred_scales=["phrygian", "harmonic_minor"],
        progression_pool=[[1, 2, 1, 2], [1, 7, 6, 7]],
        groove_type="808mafia_drill",
        lead_style="southside_siren",
        bass_style="808_glide",
        humanize_timing_ms=0.0,
        lead_reverb=(0.60, 0.18),
        lead_delay=(0.5, 0.25, 0.22),
        chord_q=24.0,
        chord_reverb=(0.65, 0.20),
        bed_gain_mul=0.52,
        melody_mix=0.95,
        chord_mix=0.78,
        bass_mix=1.25,
        special_flags={"hard_clipper": True}
    ),
    "travis_mikedean": ArtistProfile(
        id="travis_mikedean",
        name="Travis Scott & Mike Dean (Psychedelic Trap)",
        track_title_hint="Sicko Mode / Goosebumps",
        genre="trap",
        bpm_default=134.0,
        bpm_min=128.0,
        bpm_max=138.0,
        preferred_scales=["dorian", "natural_minor"],
        progression_pool=[[1, 7, 4, 6], [1, 6, 3, 7]],
        groove_type="travis_psychedelic",
        lead_style="mikedean_moog",
        bass_style="808_glide",
        humanize_timing_ms=0.0,
        lead_reverb=(0.88, 0.35),
        lead_delay=(0.75, 0.45, 0.35),
        chord_q=28.0,
        chord_reverb=(0.85, 0.32),
        bed_gain_mul=0.62,
        melody_mix=0.96,
        chord_mix=0.82,
        bass_mix=1.18,
        special_flags={"moog_overdrive": True}
    ),
    "pierre_bourne": ArtistProfile(
        id="pierre_bourne",
        name="Pi'erre Bourne (Playful Video Game Trap)",
        track_title_hint="Magnolia Bouncy Pluck",
        genre="trap",
        bpm_default=144.0,
        bpm_min=140.0,
        bpm_max=148.0,
        preferred_scales=["major_pentatonic", "dorian"],
        progression_pool=[[1, 4, 6, 5], [1, 5, 6, 4]],
        groove_type="pierre_bouncy",
        lead_style="pierre_flute_pluck",
        bass_style="808_glide",
        humanize_timing_ms=0.0,
        lead_reverb=(0.72, 0.22),
        lead_delay=(0.5, 0.35, 0.28),
        chord_q=20.0,
        chord_reverb=(0.70, 0.22),
        bed_gain_mul=0.58,
        melody_mix=0.98,
        chord_mix=0.82,
        bass_mix=1.12,
        special_flags={"game_tone": True}
    ),
    "murda_beatz": ArtistProfile(
        id="murda_beatz",
        name="Murda Beatz (Crisp Radio Trap)",
        track_title_hint="Motorsport / Nice For What",
        genre="trap",
        bpm_default=136.0,
        bpm_min=132.0,
        bpm_max=140.0,
        preferred_scales=["natural_minor"],
        progression_pool=[[1, 6, 7, 5], [1, 4, 7, 6]],
        groove_type="murda_radio",
        lead_style="murda_bell_box",
        bass_style="808_glide",
        humanize_timing_ms=0.0,
        lead_reverb=(0.68, 0.22),
        lead_delay=(0.5, 0.30, 0.25),
        chord_q=22.0,
        chord_reverb=(0.68, 0.22),
        bed_gain_mul=0.60,
        melody_mix=0.95,
        chord_mix=0.82,
        bass_mix=1.16,
        special_flags={"fast_rolls": True}
    ),
    "djmustard_ratchet": ArtistProfile(
        id="djmustard_ratchet",
        name="DJ Mustard (West Coast Ratchet)",
        track_title_hint="Pure Water / Rack City",
        genre="trap",
        bpm_default=98.0,
        bpm_min=96.0,
        bpm_max=100.0,  # Narrow ratchet pocket
        preferred_scales=["natural_minor"],
        progression_pool=[[1, 1, 1, 1], [1, 1, 7, 7]],
        groove_type="mustard_ratchet",
        lead_style="mustard_stab",
        bass_style="synth_sub",
        humanize_timing_ms=0.0,
        lead_reverb=(0.30, 0.08),  # The driest, most spacious profile in the set
        lead_delay=(0.5, 0.12, 0.10),
        chord_q=16.0,
        chord_reverb=(0.35, 0.10),
        bed_gain_mul=0.48,
        melody_mix=0.92,
        chord_mix=0.76,
        bass_mix=1.10,
        special_flags={"silence_instrument": True}
    ),

    # ── 3. GENRE: HIP-HOP ─────────────────────────────────────────────────────
    "drdre_scottstorch_gfunk": ArtistProfile(
        id="drdre_scottstorch_gfunk",
        name="Dr. Dre & Scott Storch (West Coast G-Funk)",
        track_title_hint="Still D.R.E. Piano & Whistle",
        genre="hiphop",
        bpm_default=94.0,
        bpm_min=92.0,
        bpm_max=96.0,
        preferred_scales=["natural_minor", "harmonic_minor"],
        progression_pool=[[1, 7, 6, 7], [1, 4, 7, 5]],
        groove_type="gfunk_pocket",
        lead_style="dre_storch_piano",
        bass_style="horn_punctuation",  # Subterranean horn-synth bass punctuation
        humanize_timing_ms=1.5,
        lead_reverb=(0.50, 0.14),
        lead_delay=(0.5, 0.20, 0.16),
        chord_q=22.0,
        chord_reverb=(0.82, 0.28),  # Subtle string pad surges far back
        bed_gain_mul=0.68,
        melody_mix=0.98,  # Piano dry and forward, whistle centered and soaring
        chord_mix=0.82,
        bass_mix=1.02,
        special_flags={"gfunk_whistle": True}
    ),
    "kanye_soulchop": ArtistProfile(
        id="kanye_soulchop",
        name="Kanye West (Early Soul-Chop Era)",
        track_title_hint="Through The Wire / Gold Digger",
        genre="hiphop",
        bpm_default=90.0,
        bpm_min=85.0,
        bpm_max=95.0,
        preferred_scales=["major", "natural_minor", "dorian"],
        progression_pool=[[1, 6, 4, 5], [1, 4, 7, 6], [1, 5, 6, 4]],
        groove_type="soul_boombap",
        lead_style="kanye_soulchop",  # Pitched vocal slices without formant correction
        bass_style="warm_sine",
        humanize_timing_ms=4.0,
        lead_reverb=(0.60, 0.18),
        lead_delay=(0.5, 0.25, 0.20),
        chord_q=20.0,
        chord_reverb=(0.72, 0.24),
        bed_gain_mul=0.74,  # Warm vinyl dust
        melody_mix=0.96,
        chord_mix=0.85,
        bass_mix=1.00,
        special_flags={"chipmunk_soul": True}
    ),
    "timbaland_percussive": ArtistProfile(
        id="timbaland_percussive",
        name="Timbaland (Percussive Foley Beat)",
        track_title_hint="Get Ur Freak On / Cry Me a River",
        genre="hiphop",
        bpm_default=102.0,
        bpm_min=95.0,
        bpm_max=110.0,
        preferred_scales=["natural_minor", "pentatonic_minor"],
        progression_pool=[[1, 1, 4, 1], [1, 7, 1, 7]],
        groove_type="timbaland_foley",
        lead_style="timbaland_minimal_lead",
        bass_style="synth_sub",
        humanize_timing_ms=4.5,
        lead_reverb=(0.35, 0.10),
        lead_delay=(0.5, 0.15, 0.12),
        chord_q=16.0,
        chord_reverb=(0.45, 0.12),
        bed_gain_mul=0.76,  # Vocal/texture slices front and center
        melody_mix=0.82,  # Minimal lead: rhythm is star
        chord_mix=0.75,
        bass_mix=1.05,
        special_flags={"foley_dominant": True}
    ),
    "neptunes_minimalfunk": ArtistProfile(
        id="neptunes_minimalfunk",
        name="Pharrell & The Neptunes (Dry Minimal Funk)",
        track_title_hint="Grindin' / Drop It Like It's Hot",
        genre="hiphop",
        bpm_default=100.0,
        bpm_min=95.0,
        bpm_max=105.0,
        preferred_scales=["natural_minor", "mixolydian"],
        progression_pool=[[1, 1, 7, 1], [1, 4, 1, 4]],
        groove_type="neptunes_dry",
        lead_style="neptunes_triton_pluck",  # Korg Triton plastic square pluck
        bass_style="synth_sub",
        humanize_timing_ms=1.0,
        lead_reverb=(0.25, 0.06),  # Ultra dry, tight center pan
        lead_delay=(0.5, 0.10, 0.08),
        chord_q=18.0,
        chord_reverb=(0.30, 0.08),
        bed_gain_mul=0.50,
        melody_mix=0.92,
        chord_mix=0.75,
        bass_mix=0.98,
        special_flags={"neptunes_4count": True, "negative_space": True}
    ),
    "j_dilla_lofi": ArtistProfile(
        id="j_dilla_lofi",
        name="J Dilla (MPC Swung Boom-Bap)",
        track_title_hint="Donuts / So Far to Go",
        genre="hiphop",
        bpm_default=90.0,
        bpm_min=86.0,
        bpm_max=94.0,
        preferred_scales=["dorian", "major_seventh"],
        progression_pool=[[1, 4, 2, 5], [1, 6, 2, 5]],
        groove_type="dilla_lazy_swing",
        lead_style="dilla_rhodes",
        bass_style="karplus_bass",
        humanize_timing_ms=6.0,  # Unquantized MPC lazy dragging snare
        lead_reverb=(0.80, 0.26),
        lead_delay=(0.5, 0.35, 0.24),
        chord_q=20.0,
        chord_reverb=(0.85, 0.32),
        bed_gain_mul=0.75,  # Vinyl tape warmth
        melody_mix=0.90,
        chord_mix=0.88,
        bass_mix=0.96,
        special_flags={"lazy_drag": True}
    ),
    "nujabes_jazzhop": ArtistProfile(
        id="nujabes_jazzhop",
        name="Nujabes (Atmospheric Jazzhop)",
        track_title_hint="Aruarian Dance / Feather",
        genre="hiphop",
        bpm_default=88.0,
        bpm_min=84.0,
        bpm_max=92.0,
        preferred_scales=["dorian", "natural_minor"],
        progression_pool=[[1, 4, 7, 3], [6, 2, 5, 1]],
        groove_type="nujabes_swung",
        lead_style="nujabes_piano_guitar",
        bass_style="karplus_bass",
        humanize_timing_ms=4.0,
        lead_reverb=(0.85, 0.30),
        lead_delay=(0.5, 0.32, 0.22),
        chord_q=22.0,
        chord_reverb=(0.88, 0.32),
        bed_gain_mul=0.72,
        melody_mix=0.94,
        chord_mix=0.88,
        bass_mix=0.94,
        special_flags={"jazz_voicing": True}
    ),

    # ── 4. GENRE: RAP ─────────────────────────────────────────────────────────
    "daftpunk_frenchtouch": ArtistProfile(
        id="daftpunk_frenchtouch",
        name="Daft Punk (French Touch Electro-Hop)",
        track_title_hint="Harder Better Faster Stronger",
        genre="rap",
        bpm_default=124.0,
        bpm_min=120.0,
        bpm_max=128.0,
        preferred_scales=["natural_minor", "dorian"],
        progression_pool=[[1, 7, 6, 7], [1, 4, 7, 5]],
        groove_type="french_touch_hop",
        lead_style="daft_punk_talkbox",
        bass_style="synth_sub",
        humanize_timing_ms=0.0,
        lead_reverb=(0.68, 0.20),
        lead_delay=(0.5, 0.30, 0.25),
        chord_q=24.0,
        chord_reverb=(0.70, 0.22),
        bed_gain_mul=0.64,
        melody_mix=0.98,
        chord_mix=0.86,
        bass_mix=1.04,
        special_flags={"resonant_sweep": True}
    ),
    "eminem_bassbrothers": ArtistProfile(
        id="eminem_bassbrothers",
        name="Eminem & Bass Brothers (Detroit Bounce)",
        track_title_hint="The Real Slim Shady Pluck",
        genre="rap",
        bpm_default=106.0,
        bpm_min=102.0,
        bpm_max=108.0,
        preferred_scales=["harmonic_minor", "natural_minor"],
        progression_pool=[[1, 5, 6, 5], [1, 4, 1, 5]],
        groove_type="eminem_bounce",
        lead_style="eminem_harpsichord",
        bass_style="synth_sub",
        humanize_timing_ms=1.5,
        lead_reverb=(0.40, 0.12),
        lead_delay=(0.5, 0.18, 0.14),
        chord_q=18.0,
        chord_reverb=(0.50, 0.14),
        bed_gain_mul=0.62,
        melody_mix=0.96,
        chord_mix=0.80,
        bass_mix=1.05,
        special_flags={"staccato_earworm": True}
    ),
    "kendrick_sounwave": ArtistProfile(
        id="kendrick_sounwave",
        name="Kendrick Lamar & Sounwave (Compton Trap-Rap)",
        track_title_hint="HUMBLE. / Alright Riff",
        genre="rap",
        bpm_default=150.0,
        bpm_min=140.0,
        bpm_max=156.0,
        preferred_scales=["natural_minor", "phrygian"],
        progression_pool=[[1, 1, 6, 7], [1, 2, 1, 2]],
        groove_type="kendrick_halftime",
        lead_style="kendrick_piano_stab",
        bass_style="808_glide",
        humanize_timing_ms=0.0,
        lead_reverb=(0.65, 0.20),
        lead_delay=(0.5, 0.28, 0.22),
        chord_q=26.0,
        chord_reverb=(0.70, 0.22),
        bed_gain_mul=0.60,
        melody_mix=0.96,
        chord_mix=0.82,
        bass_mix=1.20,
        special_flags={"clipped_808": True}
    ),
    "run_dmc_rickrubin": ArtistProfile(
        id="run_dmc_rickrubin",
        name="Rick Rubin (80s Rock-Rap)",
        track_title_hint="Walk This Way 808 Crunch",
        genre="rap",
        bpm_default=104.0,
        bpm_min=100.0,
        bpm_max=108.0,
        preferred_scales=["pentatonic_minor", "blues"],
        progression_pool=[[1, 4, 1, 5], [1, 1, 4, 5]],
        groove_type="rickrubin_rockrap",
        lead_style="rockrap_power_stab",
        bass_style="synth_sub",
        humanize_timing_ms=0.0,
        lead_reverb=(0.55, 0.16),
        lead_delay=(0.5, 0.20, 0.15),
        chord_q=16.0,
        chord_reverb=(0.60, 0.18),
        bed_gain_mul=0.65,
        melody_mix=0.98,
        chord_mix=0.85,
        bass_mix=1.05,
        special_flags={"crunch_guitar": True}
    ),
    "mf_doom_villain": ArtistProfile(
        id="mf_doom_villain",
        name="MF DOOM (Vintage Comic Lo-Fi Rap)",
        track_title_hint="Doomsday / Madvillainy",
        genre="rap",
        bpm_default=92.0,
        bpm_min=88.0,
        bpm_max=95.0,
        preferred_scales=["dorian", "harmonic_minor"],
        progression_pool=[[1, 4, 7, 3], [6, 2, 5, 1]],
        groove_type="doom_swing",
        lead_style="doom_cartoon_sample",
        bass_style="karplus_bass",
        humanize_timing_ms=5.0,
        lead_reverb=(0.75, 0.24),
        lead_delay=(0.5, 0.30, 0.20),
        chord_q=22.0,
        chord_reverb=(0.80, 0.26),
        bed_gain_mul=0.78,  # High dusty sample warmth
        melody_mix=0.92,
        chord_mix=0.86,
        bass_mix=0.98,
        special_flags={"vinyl_noise": True}
    ),

    # ── 5. GENRE: MINIMAL ─────────────────────────────────────────────────────
    "four_tet_textural": ArtistProfile(
        id="four_tet_textural",
        name="Four Tet (Organic Textural Micro-House)",
        track_title_hint="Two Thousand and Seventeen",
        genre="minimal",
        bpm_default=126.0,
        bpm_min=124.0,
        bpm_max=128.0,
        preferred_scales=["natural_minor", "dorian"],
        progression_pool=[[1, 6, 3, 7], [1, 4, 6, 5]],
        groove_type="fourtet_skipping",
        lead_style="four_tet_mallet",  # Wooden marimba / kalimba
        bass_style="synth_sub",
        humanize_timing_ms=2.5,
        lead_reverb=(0.82, 0.26),
        lead_delay=(0.75, 0.40, 0.32),
        chord_q=26.0,
        chord_reverb=(0.82, 0.26),
        bed_gain_mul=0.68,
        melody_mix=0.92,
        chord_mix=0.80,
        bass_mix=0.98,
        special_flags={"organic_foley": True}
    ),
    "burial_futuregarage": ArtistProfile(
        id="burial_futuregarage",
        name="Burial (South London Future Garage)",
        track_title_hint="Archangel Rain & Vinyl",
        genre="minimal",
        bpm_default=134.0,
        bpm_min=130.0,
        bpm_max=138.0,
        preferred_scales=["natural_minor", "phrygian"],
        progression_pool=[[1, 6, 4, 7], [1, 7, 6, 7]],
        groove_type="burial_2step",
        lead_style="burial_vocal_ghost",
        bass_style="synth_sub",
        humanize_timing_ms=5.0,  # Unquantized skittering 2-step
        lead_reverb=(0.95, 0.42),
        lead_delay=(0.75, 0.48, 0.38),
        chord_q=28.0,
        chord_reverb=(0.92, 0.40),
        bed_gain_mul=0.82,  # Heavy vinyl rain & crackle
        melody_mix=0.88,
        chord_mix=0.82,
        bass_mix=1.12,
        special_flags={"vinyl_rain": True, "reese_sub": True}
    ),
    "aphex_twin_braindance": ArtistProfile(
        id="aphex_twin_braindance",
        name="Aphex Twin (Braindance / Acid IDM)",
        track_title_hint="Selected Ambient Works 85-92",
        genre="minimal",
        bpm_default=124.0,
        bpm_min=120.0,
        bpm_max=128.0,
        preferred_scales=["natural_minor", "lydian"],
        progression_pool=[[1, 7, 4, 5], [1, 6, 2, 5]],
        groove_type="aphex_acid_808",
        lead_style="aphex_acid_squelch",
        bass_style="synth_sub",
        humanize_timing_ms=0.0,
        lead_reverb=(0.75, 0.25),
        lead_delay=(0.5, 0.35, 0.28),
        chord_q=30.0,  # Sharp acid filter resonance
        chord_reverb=(0.70, 0.22),
        bed_gain_mul=0.62,
        melody_mix=0.96,
        chord_mix=0.80,
        bass_mix=1.04,
        special_flags={"tb303_squelch": True}
    ),
    "jamie_xx_ukbass": ArtistProfile(
        id="jamie_xx_ukbass",
        name="Jamie xx (UK Bass & Steel Pan)",
        track_title_hint="Gosh / Loud Places",
        genre="minimal",
        bpm_default=122.0,
        bpm_min=120.0,
        bpm_max=125.0,
        preferred_scales=["major", "dorian"],
        progression_pool=[[1, 4, 6, 5], [1, 5, 4, 1]],
        groove_type="jamiexx_shuffle",
        lead_style="jamiexx_steel_pan",
        bass_style="synth_sub",
        humanize_timing_ms=2.0,
        lead_reverb=(0.84, 0.28),
        lead_delay=(0.75, 0.38, 0.30),
        chord_q=22.0,
        chord_reverb=(0.80, 0.25),
        bed_gain_mul=0.66,
        melody_mix=0.94,
        chord_mix=0.84,
        bass_mix=1.14,
        special_flags={"dub_sub": True}
    ),
    "bonobo_organic": ArtistProfile(
        id="bonobo_organic",
        name="Bonobo (Organic World Electronica)",
        track_title_hint="Cirrus Kalimba Pulse",
        genre="minimal",
        bpm_default=118.0,
        bpm_min=114.0,
        bpm_max=122.0,
        preferred_scales=["dorian", "mixolydian"],
        progression_pool=[[1, 4, 7, 5], [1, 6, 4, 5]],
        groove_type="bonobo_organic_groove",
        lead_style="bonobo_kalimba",
        bass_style="karplus_bass",
        humanize_timing_ms=3.5,
        lead_reverb=(0.80, 0.26),
        lead_delay=(0.75, 0.35, 0.28),
        chord_q=20.0,
        chord_reverb=(0.78, 0.24),
        bed_gain_mul=0.70,
        melody_mix=0.92,
        chord_mix=0.86,
        bass_mix=0.98,
        special_flags={"world_shaker": True}
    ),

    # ── 6. GENRE: RHYTHMIC (LATIN, DEMBOW, DANCE) ──────────────────────────────
    "major_lazer_moombahton": ArtistProfile(
        id="major_lazer_moombahton",
        name="Major Lazer & Diplo (Moombahton / Dancehall)",
        track_title_hint="Lean On / Pon De Floor",
        genre="rhythmic",
        bpm_default=110.0,
        bpm_min=106.0,
        bpm_max=114.0,
        preferred_scales=["natural_minor", "dorian"],
        progression_pool=[[1, 6, 7, 1], [1, 7, 6, 7]],
        groove_type="dembow_clave",
        lead_style="moombahton_synth_horn",
        bass_style="synth_sub",
        humanize_timing_ms=1.0,
        lead_reverb=(0.60, 0.18),
        lead_delay=(0.5, 0.25, 0.20),
        chord_q=20.0,
        chord_reverb=(0.65, 0.20),
        bed_gain_mul=0.64,
        melody_mix=0.96,
        chord_mix=0.82,
        bass_mix=1.12,
        special_flags={"dembow_kick": True}
    ),
    "badbunny_tainy": ArtistProfile(
        id="badbunny_tainy",
        name="Bad Bunny & Tainy (Futuristic Reggaeton)",
        track_title_hint="Dákiti / Safaera",
        genre="rhythmic",
        bpm_default=94.0,
        bpm_min=90.0,
        bpm_max=96.0,
        preferred_scales=["natural_minor", "harmonic_minor"],
        progression_pool=[[1, 6, 3, 7], [1, 7, 6, 5]],
        groove_type="reggaeton_dembow",
        lead_style="tainy_synthwave_pad",
        bass_style="808_glide",
        humanize_timing_ms=0.0,
        lead_reverb=(0.75, 0.25),
        lead_delay=(0.5, 0.30, 0.24),
        chord_q=22.0,
        chord_reverb=(0.78, 0.26),
        bed_gain_mul=0.62,
        melody_mix=0.94,
        chord_mix=0.86,
        bass_mix=1.18,
        special_flags={"puerto_rico_dembow": True}
    ),
    "stromae_electrodance": ArtistProfile(
        id="stromae_electrodance",
        name="Stromae (European Melancholic Dance)",
        track_title_hint="Alors on danse / Papaoutai",
        genre="rhythmic",
        bpm_default=122.0,
        bpm_min=118.0,
        bpm_max=124.0,
        preferred_scales=["natural_minor", "harmonic_minor"],
        progression_pool=[[1, 6, 4, 5], [1, 7, 6, 5]],
        groove_type="stromae_eurodance",
        lead_style="stromae_brass_trumpet",
        bass_style="synth_sub",
        humanize_timing_ms=0.0,
        lead_reverb=(0.65, 0.20),
        lead_delay=(0.5, 0.22, 0.18),
        chord_q=20.0,
        chord_reverb=(0.68, 0.22),
        bed_gain_mul=0.65,
        melody_mix=0.98,
        chord_mix=0.85,
        bass_mix=1.05,
        special_flags={"trumpet_hook": True}
    ),
    "rosalia_el_guincho": ArtistProfile(
        id="rosalia_el_guincho",
        name="Rosalía & El Guincho (Modern Flamenco Pop)",
        track_title_hint="Malamente (Palmas & 808s)",
        genre="rhythmic",
        bpm_default=102.0,
        bpm_min=98.0,
        bpm_max=106.0,
        preferred_scales=["phrygian", "harmonic_minor"],
        progression_pool=[[1, 2, 1, 2], [1, 7, 6, 7]],
        groove_type="flamenco_palmas",
        lead_style="rosalia_vocal_drop",
        bass_style="808_glide",
        humanize_timing_ms=2.0,
        lead_reverb=(0.70, 0.22),
        lead_delay=(0.5, 0.25, 0.20),
        chord_q=24.0,
        chord_reverb=(0.72, 0.24),
        bed_gain_mul=0.70,
        melody_mix=0.96,
        chord_mix=0.82,
        bass_mix=1.14,
        special_flags={"palmas_claps": True}
    ),
    "santana_latinrock": ArtistProfile(
        id="santana_latinrock",
        name="Carlos Santana (Latin Rock & Congas)",
        track_title_hint="Smooth / Oye Como Va",
        genre="rhythmic",
        bpm_default=116.0,
        bpm_min=112.0,
        bpm_max=120.0,
        preferred_scales=["dorian", "natural_minor"],
        progression_pool=[[1, 4, 1, 4], [1, 7, 4, 5]],
        groove_type="latin_conga_rock",
        lead_style="santana_lead_guitar",
        bass_style="karplus_bass",
        humanize_timing_ms=5.0,
        lead_reverb=(0.75, 0.24),
        lead_delay=(0.5, 0.28, 0.22),
        chord_q=18.0,
        chord_reverb=(0.70, 0.22),
        bed_gain_mul=0.68,
        melody_mix=0.98,
        chord_mix=0.86,
        bass_mix=1.02,
        special_flags={"conga_percussion": True}
    ),

    # ── 7. GENRE: AMBIENT / NONE ──────────────────────────────────────────────
    "brian_eno_generative": ArtistProfile(
        id="brian_eno_generative",
        name="Brian Eno (Generative Shimmer Ambient)",
        track_title_hint="Music for Airports",
        genre="none",
        bpm_default=68.0,
        bpm_min=64.0,
        bpm_max=72.0,
        preferred_scales=["major", "lydian"],
        progression_pool=[[1, 4, 5, 1], [1, 6, 4, 5]],
        groove_type="ambient_still",
        lead_style="brian_eno_piano_shimmer",
        bass_style="sub_drone",
        humanize_timing_ms=0.0,
        lead_reverb=(0.98, 0.60),  # Infinite reverb wash
        lead_delay=(0.75, 0.55, 0.45),
        chord_q=12.0,
        chord_reverb=(0.98, 0.58),
        bed_gain_mul=0.88,  # Input noise bed IS the composition
        melody_mix=0.55,  # Subtle ghost melody
        chord_mix=0.84,
        bass_mix=0.55,
        special_flags={"infinite_reverb": True}
    ),
    "stars_of_the_lid": ArtistProfile(
        id="stars_of_the_lid",
        name="Stars of the Lid (Drone Symphony)",
        track_title_hint="And Their Refinement Swell",
        genre="none",
        bpm_default=60.0,
        bpm_min=55.0,
        bpm_max=65.0,
        preferred_scales=["natural_minor", "dorian"],
        progression_pool=[[1, 1, 6, 6], [1, 4, 1, 4]],
        groove_type="ambient_still",
        lead_style="drone_string_swell",
        bass_style="sub_drone",
        humanize_timing_ms=0.0,
        lead_reverb=(0.99, 0.65),
        lead_delay=(0.75, 0.60, 0.50),
        chord_q=10.0,
        chord_reverb=(0.99, 0.62),
        bed_gain_mul=0.92,
        melody_mix=0.45,
        chord_mix=0.88,
        bass_mix=0.60,
        special_flags={"drone_swell": True}
    ),
    "tim_hecker_frost": ArtistProfile(
        id="tim_hecker_frost",
        name="Tim Hecker (Textured Digital Frost)",
        track_title_hint="Ravedeath Organ Swell",
        genre="none",
        bpm_default=70.0,
        bpm_min=65.0,
        bpm_max=74.0,
        preferred_scales=["natural_minor", "phrygian"],
        progression_pool=[[1, 7, 6, 7], [1, 2, 1, 2]],
        groove_type="ambient_still",
        lead_style="hecker_pipe_organ",
        bass_style="sub_drone",
        humanize_timing_ms=0.0,
        lead_reverb=(0.94, 0.50),
        lead_delay=(0.75, 0.50, 0.40),
        chord_q=16.0,
        chord_reverb=(0.95, 0.52),
        bed_gain_mul=0.90,
        melody_mix=0.60,
        chord_mix=0.85,
        bass_mix=0.65,
        special_flags={"frost_distortion": True}
    ),
    "harold_budd_softpiano": ArtistProfile(
        id="harold_budd_softpiano",
        name="Harold Budd (Soft-Pedal Felt Piano)",
        track_title_hint="The Pearl / Room Harmonics",
        genre="none",
        bpm_default=66.0,
        bpm_min=62.0,
        bpm_max=70.0,
        preferred_scales=["major", "dorian"],
        progression_pool=[[1, 4, 6, 5], [1, 5, 6, 4]],
        groove_type="ambient_still",
        lead_style="budd_felt_piano",
        bass_style="sub_drone",
        humanize_timing_ms=0.0,
        lead_reverb=(0.96, 0.54),
        lead_delay=(0.75, 0.48, 0.38),
        chord_q=14.0,
        chord_reverb=(0.96, 0.55),
        bed_gain_mul=0.85,
        melody_mix=0.58,
        chord_mix=0.82,
        bass_mix=0.50,
        special_flags={"felt_piano": True}
    ),
    "aphex_saw2_dark": ArtistProfile(
        id="aphex_saw2_dark",
        name="Aphex Twin (SAW II Meditative Drone)",
        track_title_hint="Selected Ambient Works Vol. II",
        genre="none",
        bpm_default=62.0,
        bpm_min=58.0,
        bpm_max=66.0,
        preferred_scales=["natural_minor"],
        progression_pool=[[1, 6, 7, 1], [1, 1, 1, 1]],
        groove_type="ambient_still",
        lead_style="aphex_tape_pad",
        bass_style="sub_drone",
        humanize_timing_ms=0.0,
        lead_reverb=(0.98, 0.58),
        lead_delay=(0.75, 0.52, 0.42),
        chord_q=14.0,
        chord_reverb=(0.98, 0.58),
        bed_gain_mul=0.88,
        melody_mix=0.52,
        chord_mix=0.85,
        bass_mix=0.55,
        special_flags={"tape_drift": True}
    ),
}


# ==============================================================================
# DISPATCH & SELECTION API
# ==============================================================================

def get_artist_by_id(artist_id: str) -> Optional[ArtistProfile]:
    """Retrieve an artist profile by unique string ID."""
    return ARTIST_PROFILES.get(artist_id)


def get_artists_for_genre(genre: str) -> List[ArtistProfile]:
    """Return all artist profiles registered under a given genre."""
    g = (genre or "pop").lower().strip()
    # Normalize aliases
    if g in ["trap", "drill"]:
        target_genre = "trap"
    elif g in ["pop", "dance", "synthpop"]:
        target_genre = "pop"
    elif g in ["hiphop", "hip_hop", "boom_bap", "boombap", "lofi"]:
        target_genre = "hiphop"
    elif g in ["rap", "electro", "french_touch"]:
        target_genre = "rap"
    elif g in ["minimal", "house", "garage"]:
        target_genre = "minimal"
    elif g in ["rhythmic", "energetic", "latin", "moombahton", "light_percussion", "percussion", "organic"]:
        target_genre = "rhythmic"
    elif g in ["none", "ambient"]:
        target_genre = "none"
    else:
        target_genre = "pop"

    matches = [p for p in ARTIST_PROFILES.values() if p.genre == target_genre]
    if not matches:
        return [ARTIST_PROFILES["ladygaga_redone_electro"]]
    return matches


def get_random_artist_for_genre(
    genre: str,
    rng: Optional[SeededRNG] = None,
    exclude_artist_ids: Optional[List[str]] = None,
    preferred_artist_id: Optional[str] = None
) -> Tuple[ArtistProfile, bool]:
    """
    Select an artist profile for the given genre.
    Supports browser-driven 'bag without replacement' cycling:
    - If preferred_artist_id is provided and valid, returns that artist directly.
    - If exclude_artist_ids is provided, picks an artist that hasn't been played yet in the current cycle.
    - When all artists for that genre have been played, the pool resets and cycle_reset=True is returned.
    """
    if preferred_artist_id and preferred_artist_id in ARTIST_PROFILES:
        return ARTIST_PROFILES[preferred_artist_id], False

    all_artists = get_artists_for_genre(genre)
    excluded = set(exclude_artist_ids or [])

    # Filter for unplayed artists in this genre
    available = [a for a in all_artists if a.id not in excluded]

    cycle_reset = False
    if not available:
        # All artists for this genre have been played! Reset the cycle.
        available = all_artists
        cycle_reset = True

    # Hard rule: For Pop auto-cycling, Electro-Pop Supersaw always plays first
    # (i.e. when it has not yet been played/excluded in the current cycle).
    # This ensures a consistent "wow" first impression regardless of prior session history.
    if not preferred_artist_id and (genre or "pop").lower().strip() in ("pop", "vocal_fusion"):
        supersaw = next((a for a in available if a.id == "ladygaga_redone_electro"), None)
        if supersaw is not None:
            return supersaw, cycle_reset

    if not preferred_artist_id and not exclude_artist_ids and available:
        # Default first roll for other genres returns the signature flagship archetype
        return available[0], False

    if rng is None:
        idx = int(np.random.randint(0, len(available)))
    else:
        idx = rng.randint(0, len(available) - 1)

    return available[idx], cycle_reset


def get_all_styles_metadata() -> List[Dict[str, Any]]:
    """Returns clean, client-facing metadata for all sonic style archetypes."""
    res = []
    for p in ARTIST_PROFILES.values():
        res.append({
            "id": p.id,
            "display_name": p.display_name,
            "vibe": p.vibe,
            "genre": p.genre,
            "bpm_default": p.bpm_default,
            "bpm_min": p.bpm_min,
            "bpm_max": p.bpm_max,
            "scales": p.preferred_scales
        })
    return res


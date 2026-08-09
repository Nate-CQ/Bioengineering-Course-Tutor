"""
Course taxonomies. Each course is broken into a granular subtopic list built
from published syllabi and standard textbook tables of contents for these
subjects (Semmlow's Circuits, Signals, and Systems for Bioengineers for
signals; Ratner et al.'s Biomaterials Science for biomaterials; standard
undergraduate human physiology and biostatistics syllabi). Granular topics
keep generated questions targeted at a specific concept instead of drifting
toward generic material.
"""

COURSES = {
    "signals_systems": {
        "name": "Bioengineering Signals and Systems",
        "description": (
            "Properties of signals and systems; signal operations on "
            "continuous and discrete signals; linear, time-invariant (LTI) "
            "systems; time-domain analysis and convolution; systems "
            "described by linear constant-coefficient differential "
            "equations; Fourier series and Fourier transform analysis; "
            "the Laplace transform; introduction to filtering; sampling "
            "and the sampling theorem. Recurring biomedical examples "
            "include the ECG, the arterial blood pressure waveform, "
            "signal coding in the auditory system and cochlear implants, "
            "and basic principles of biomedical imaging."
        ),
        "topics": [
            "Signal Classification and Properties (periodic vs. aperiodic, even/odd symmetry, energy vs. power signals)",
            "Signal Operations (time shifting, scaling, reflection, elementary signals like the unit step and impulse)",
            "System Properties (linearity, time-invariance, causality, stability, memory)",
            "LTI Systems and Convolution (impulse response, the convolution integral and sum)",
            "Linear Constant-Coefficient Differential and Difference Equations",
            "Fourier Series (periodic signal decomposition, harmonics, line spectra)",
            "Fourier Transform (transform pairs, properties, frequency-domain interpretation)",
            "Frequency Response and Transfer Functions",
            "Laplace Transform and Pole-Zero Analysis",
            "Filtering (low-pass, high-pass, band-pass; ideal vs. realizable filters)",
            "Sampling and the Sampling Theorem (Nyquist rate, aliasing, quantization)",
            "Biomedical Signal Applications (ECG waveform analysis, arterial blood pressure waveform, cochlear implant signal coding, basic biomedical imaging)",
        ],
        "quantitative": True,
    },
    "physiology": {
        "name": "Principles of Human Physiology",
        "description": (
            "Major human organ systems studied through underlying physical "
            "and chemical principles, with structure-function relationships "
            "(anatomy and histology) covered alongside physiology, and "
            "disease discussed throughout as a lens for understanding "
            "normal function and homeostatic regulation."
        ),
        "topics": [
            "Cell and Membrane Physiology (membrane transport, resting membrane potential, action potentials, channels and pumps)",
            "Homeostasis and Feedback Control (negative and positive feedback loops, control systems)",
            "Nervous System (central and peripheral organization, synaptic transmission, reflex arcs, special senses)",
            "Muscle Physiology (skeletal, cardiac, and smooth muscle contraction mechanisms; excitation-contraction coupling)",
            "Cardiovascular System (cardiac cycle, cardiac output, hemodynamics, blood pressure regulation)",
            "Respiratory System (ventilation and gas exchange, oxygen-hemoglobin dissociation, control of breathing)",
            "Renal System (glomerular filtration, tubular reabsorption and secretion, fluid and electrolyte balance)",
            "Acid-Base Balance (buffer systems, respiratory and renal compensation)",
            "Endocrine System (hormone signaling mechanisms, major regulatory axes, feedback control)",
            "Gastrointestinal System (motility, secretion, digestion, and nutrient absorption)",
        ],
        "quantitative": False,
    },
    "biomaterials": {
        "name": "Biomaterials",
        "description": (
            "Application of materials science and engineering to "
            "biomedical applications, focused on polymers, ceramics, and "
            "metals: basic material fabrication and synthesis, structure "
            "and property characterization, and applications of "
            "biomaterials, complemented by laboratory-style examples of "
            "material assessment and characterization."
        ),
        "topics": [
            "Classes of Biomaterials (metals, ceramics, polymers, composites, and natural materials compared)",
            "Polymers (polymerization mechanisms, crystallinity, common medical-grade polymers, degradation)",
            "Metals as Biomaterials (stainless steel, titanium alloys, cobalt-chromium alloys, corrosion resistance)",
            "Ceramics as Biomaterials (bioinert vs. bioactive ceramics, hydroxyapatite, brittleness and fracture)",
            "Mechanical Properties and Characterization (stress-strain behavior, elastic modulus, fatigue, hardness testing)",
            "Surface Properties and Surface Modification (wettability, protein adsorption, coatings)",
            "Biocompatibility and Host Response (foreign body reaction, inflammation, immune response to implants)",
            "Degradation and Corrosion (hydrolytic and enzymatic degradation, bio-corrosion mechanisms)",
            "Sterilization and Regulatory Considerations for Medical Devices",
            "Clinical Applications (orthopedic implants, cardiovascular devices, drug delivery systems, tissue engineering scaffolds)",
        ],
        "quantitative": True,
    },
    "biostatistics": {
        "name": "Biological Data Science I: Fundamentals of Biostatistics",
        "description": (
            "Fundamental concepts in applied probability, exploratory data "
            "analysis, and statistical inference, taught in the context of "
            "solving biomedical research problems."
        ),
        "topics": [
            "Probability Fundamentals (probability rules, conditional probability, Bayes' theorem)",
            "Random Variables and Probability Distributions (binomial, Poisson, normal, exponential)",
            "Descriptive Statistics and Exploratory Data Analysis (measures of center and spread, data visualization)",
            "Sampling Distributions and the Central Limit Theorem",
            "Point and Interval Estimation (confidence intervals)",
            "Hypothesis Testing (null and alternative hypotheses, p-values, Type I and Type II error, t-tests)",
            "Analysis of Variance (ANOVA)",
            "Correlation and Simple Linear Regression",
            "Contingency Tables and Categorical Data Analysis (chi-square tests)",
            "Study Design in Biomedical Research (randomized trials, cohort and case-control studies, bias and confounding)",
        ],
        "quantitative": True,
    },
}

QUESTION_TYPES = {
    "multiple_choice": "Multiple Choice",
    "fill_in_blank": "Fill in the Blank",
    "short_answer": "Short Answer",
}

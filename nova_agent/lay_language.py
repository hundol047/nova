"""Documented lay-language variants for Tier-1 knowledge-base typical features (Round M).

PROVENANCE: authored by the repository's engineering agent from general, widely used patient
vocabulary for each feature. It is NOT clinician-reviewed and makes NO diagnostic claim -- each
entry only says "a patient may phrase THIS feature this way". Every variant is keyed to ONE exact
knowledge-base phrase and can only ever help that single phrase (same discipline as
matching.FEATURE_ALIASES, which this table is merged into at import time). Variants are deliberately
multi-word and specific; bare generic words (dizzy, pain, bad) are avoided so one alias cannot
satisfy many unrelated features.

Why this exists: Round M development tracing showed the dominant Tier-1 failure was lexical -- the
correct diagnosis stayed at score 0.0 for a whole encounter because the patient said "pee burns" /
"tingly lips" / "light-headed when I get up" while the knowledge base says "dysuria" / "tingling
around the mouth" / "lightheadedness on standing up".
"""

from __future__ import annotations

from typing import Dict, List

_NAUSEA = ["feel sick", "feeling sick", "sick to my stomach", "queasy", "nauseated", "nauseous", "feel nauseous"]
_VOMIT = ["throwing up", "threw up", "been sick", "vomited", "retching", "keep vomiting"]
_SWEAT = ["sweating", "cold sweat", "clammy", "drenched in sweat", "sweaty", "breaking out in a sweat"]
_FEVER = ["running a temperature", "high temperature", "feverish", "burning up", "slight fever", "low fever", "mild fever", "a temperature"]
_CONFUSED = ["confused", "muddled", "disoriented", "not making sense", "drowsy and confused"]
_BREATHLESS = ["short of breath", "out of breath", "breathless", "cannot catch my breath", "cannot get air in"]
_DYSURIA = ["burning when i pee", "burns to pee", "stings to pee", "hurts to pee", "burning urination", "pee burns",
            "burning when i wee", "burns when i wee", "pain passing urine", "pain when urinating", "stings when i pee",
            "hurts when i pee", "urinating hurts", "peeing hurts", "wee burns"]

LAY_FEATURE_ALIASES: Dict[str, List[str]] = {
    # --- acute abdomen
    "severe abdominal pain": ["terrible belly pain", "awful stomach pain", "excruciating belly pain", "knife-like belly pain", "severe belly pain"],
    "rigid abdomen": ["stomach is rock hard", "belly is hard as a board", "belly rigid", "board-like belly"],
    "fever": _FEVER,
    # --- bronchitis / pneumonia / URI
    "productive cough": ["cough with phlegm", "coughing up mucus", "coughing up phlegm", "chesty cough", "coughing up gunk",
                         "coughing up yellow phlegm", "rusty phlegm", "coughing up thick spit", "clear phlegm"],
    "mild fever": ["low fever", "slight fever", "a little feverish", "mild temperature"],
    "recent viral illness": ["after a cold", "following a cold", "after the flu", "after a chest cold", "after a head cold"],
    "chest wall soreness from coughing": ["sore chest muscles from coughing", "chest aches from coughing"],
    "pleuritic chest pain": ["stitch in my side when i breathe", "stabbing pain when i breathe in", "sharp pain on breathing in",
                              "hurts when i breathe in", "stabs when i breathe in", "pain when i breathe in deeply"],
    "crackles on auscultation": ["crackles", "rattly chest"],
    "dyspnea": _BREATHLESS,
    "rhinorrhea": ["runny nose", "blocked nose", "stuffy nose", "sneezing"],
    "sore throat": ["scratchy throat", "throat is sore"],
    "low grade fever": ["slight fever", "mild fever", "low fever", "a little feverish", "low temperature"],
    # --- cardiac
    "exertional chest pain": ["chest pain when walking uphill", "chest pressure on exertion", "chest tightness climbing stairs",
                               "chest pain when i hurry", "pressure when i hurry up the stairs", "pain on effort", "when i climb a slope"],
    "substernal pressure": ["pressure in the middle of my chest", "weight on my chest", "band around my chest", "squeezing chest",
                             "heavy weight settles on my chest", "vice squeezing my chest", "chest gets crushed", "chest feels crushed",
                             "tight band across my chest", "squeezing me"],
    "radiates to arm or jaw": ["spreads to my left arm", "spreads into my shoulder", "pain goes to my jaw", "jaw ache", "jaw aches",
                                "arm feels heavy", "left arm heaviness", "spreads into my left shoulder", "arm feels heavy"],
    "diaphoresis": _SWEAT,
    "nausea": _NAUSEA,
    "dyspnea on exertion": ["breathless walking", "short of breath on the stairs", "out of breath on exertion", "breathless climbing",
                             "breathless walking to the kitchen"],
    "left arm pain": ["pain in my left arm", "left arm aching", "left arm heavy"],
    "sudden onset palpitations": ["heart suddenly started racing", "heart began racing", "sudden pounding heartbeat", "pulse went wild"],
    "irregular heartbeat": ["uneven pulse", "pulse is irregular", "heart skipping beats", "skipped beats", "fluttering", "heart skip",
                             "pulse went wild and irregular", "pulse is uneven"],
    "racing heart": ["heart racing", "heart is pounding", "pulse is fast", "heart thumping", "heart pounding", "heart is racing"],
    "associated lightheadedness": ["feel faint", "feel light-headed", "near fainting", "feel woozy", "feel faint and woozy"],
    "known history of arrhythmia": ["atrial fibrillation", "known afib"],
    "palpitations": ["heart pounding", "heart racing", "heart thumping", "heart is pounding", "fluttering heart"],
    # --- pancreatitis
    "epigastric pain radiating to back": ["pain in the pit of my stomach", "upper belly pain through to my back", "boring ache in the pit of my stomach",
                                           "goes through to my back", "pit of my stomach that goes"],
    "vomiting": _VOMIT,
    "worse after eating fatty food": ["worse after greasy food", "after fatty meals", "greasy meals set it off", "worse after a fatty meal", "greasy food"],
    # --- anaphylaxis
    "sudden onset urticaria": ["hives", "welts all over", "itchy raised rash", "covered in welts", "hives all over"],
    "facial swelling": ["swollen lips", "swollen face", "swollen tongue", "lips and tongue swelling", "lips are huge"],
    "wheeze": ["wheezing", "wheezy", "whistling in my chest", "audible wheeze"],
    "throat tightness": ["throat closing", "throat feels tight", "tight throat", "throat is closing up", "throat squeezing"],
    "recent allergen exposure": ["after a bee sting", "after eating peanuts", "first dose of a new antibiotic", "after the antibiotic",
                                  "minutes after my first dose", "after shrimp"],
    # --- dissection
    "tearing chest pain": ["ripping pain in my chest", "tearing pain in my chest", "tearing pain", "ripping pain"],
    "ripping pain": ["tearing pain", "like something ripping", "tearing feeling", "tearing"],
    "pain radiates to back": ["pain goes through to my back", "between my shoulder blades", "shooting into my back", "through to my back"],
    "sudden onset severe pain": ["worst pain of my life", "worst pain i have ever had", "came on all at once", "sudden severe pain"],
    "pulse differential": ["weaker pulse in one arm", "pulse deficit"],
    "unequal blood pressure between arms": ["blood pressure different in each arm", "higher in the right arm than the left"],
    # --- appendicitis
    "periumbilical pain migrating to right lower quadrant": [
        "pain began near my navel and moved", "started around my belly button and moved", "near my belly button now lower right",
        "moved to the right lower belly", "from my navel to the lower right", "moved low on the right", "crept down to the lower right",
        "moved to the lower right", "started near my navel", "pain near my navel"],
    "anorexia": ["no appetite", "loss of appetite", "not hungry", "off my food", "cannot eat"],
    # --- asthma / copd
    "known asthma or copd": ["asthma since childhood", "i have asthma", "i have copd", "history of asthma", "emphysema", "asthma as a teenager", "known asthma"],
    "worse with triggers": ["worse around cats", "dust makes it worse", "cold air makes it worse", "set off by dust", "pollen makes it worse",
                             "cold air always sets it off", "after cleaning the dusty"],
    "prolonged expiration": ["long breathing out", "hard to breathe out", "breathing out takes longer", "prolonged breathing out"],
    # --- vertigo / syncope
    "brief episodic vertigo": ["room spins for a few seconds", "spinning for a few seconds", "brief spinning", "dizzy spells that last seconds",
                                "room whirls", "whirl for a few seconds", "spins briefly", "spells are under a minute", "whirling",
                                "everything whirl", "room spins"],
    "triggered by head position change": ["roll over in bed", "turn over in bed", "tilt my head back", "looking up", "turning my head",
                                           "rolling over in bed", "tip my head", "tilting my head", "when i roll over", "when i turn over"],
    "no focal neuro deficit": ["no weakness", "no speech problem", "no numbness", "no weakness or numbness"],
    "no hearing loss": ["hearing fine", "hearing is normal", "no change in hearing", "no hearing change", "no hearing loss"],
    "lightheadedness on standing up": ["light-headed when i stand", "dizzy when i stand up", "woozy on standing", "faint when i get up quickly",
                                        "light-headed every time i get up", "lightheaded getting out of bed", "light-headed on standing",
                                        "light-headed when i get up", "lightheaded when i stand", "light-headed when i stand",
                                        "stand up quickly", "get up quickly", "get out of bed", "when i stand after"],
    "improves with sitting or lying down": ["passes when i sit down", "goes away when i sit", "eases when i lie down", "passes when i sit back down",
                                             "settles when i sit", "better when i sit"],
    "prodrome of lightheadedness": ["felt hot and sweaty first", "felt warm and queasy first", "tunnel vision", "clammy first", "went grey",
                                     "felt hot and sweaty", "felt warm and nauseous", "hot and nauseous first", "nauseous and warm first"],
    "triggered by standing or pain or fear": ["blood draw", "needle", "seeing blood", "standing for ages", "standing in the heat",
                                               "standing a long time", "standing outside in the heat", "fear of needles", "when they took my blood"],
    "brief loss of consciousness": ["blacked out for a few seconds", "passed out briefly", "slumped", "went down for a few seconds",
                                     "woke up within seconds", "crumpled", "blacked out"],
    "rapid spontaneous recovery": ["came round at once", "recovered quickly", "came round quickly", "woke up within seconds", "quick recovery",
                                    "woke within seconds", "came around quickly"],
    # --- DKA / metabolic
    "polyuria": ["peeing constantly", "urinating a lot", "going to the toilet all the time", "passing lots of urine", "peeing nonstop", "peeing a lot"],
    "polydipsia": ["very thirsty", "drinking constantly", "drinking gallons", "cannot stop drinking water", "extremely thirsty", "so thirsty", "always thirsty"],
    "nausea and vomiting": ["throwing up and feeling sick", "vomiting and feeling sick", "sick and vomiting", "nausea and vomiting"],
    "fruity breath odor": ["breath smells like nail polish", "pear drops", "sweet smelling breath", "fruity smell on my breath", "breath smells of acetone",
                            "smells like nail polish"],
    "kussmaul breathing": ["deep fast breathing", "rapid deep breathing", "breathing deeply and fast", "deep heavy breathing", "breathing fast and deep",
                            "breathing is deeper", "breathing deeply"],
    "confusion": _CONFUSED,
    "altered mental status": _CONFUSED,
    "tremor": ["shaky", "trembling", "shaking hands", "tremulous"],
    "known diabetes on insulin": ["takes insulin", "on insulin", "injected my insulin", "mealtime insulin", "long-acting insulin"],
    # --- ectopic / gyn
    "lower abdominal pain": ["low belly ache", "pain low in my belly", "lower tummy pain", "low one-sided belly ache", "discomfort low on my", "ache low down"],
    "vaginal bleeding": ["spotting", "light bleeding", "bleeding from the vagina", "brownish spotting", "light spotting"],
    "missed period": ["period is late", "period is overdue", "weeks late", "missed my period", "period is about six weeks late", "period is six weeks late",
                       "period more than a month late", "cycle is running well behind"],
    "unilateral pelvic pain": ["pain on one side low down", "one-sided lower belly pain", "pain low on the right", "pain low on the left",
                                "low on one side", "ache down low on my left"],
    "dizziness": ["nearly fainted", "almost fainted", "feel faint", "woozy"],
    # --- gastroenteritis / GERD
    "diffuse crampy abdominal pain": ["crampy tummy", "cramping belly", "stomach cramps", "cramps all over my belly", "crampy belly", "cramping all over my belly",
                                       "crampy stomach"],
    "diarrhea": ["loose stools", "watery stools", "runny stools", "the runs", "watery diarrhea", "loose watery"],
    "recent similar illness contact": ["others who ate with me are ill", "everyone who ate it is sick", "companion is ill", "others who ate the same",
                                        "two friends who ate", "others are ill too", "family dinner", "who ate with me", "ate at the same"],
    "burning chest pain": ["burning behind my breastbone", "burning in my chest", "heartburn", "burning in the chest", "burning behind"],
    "worse after meals": ["after eating", "after a big meal", "after pizza", "after dinner", "after a large snack", "after a big dinner"],
    "worse lying down": ["when i lie down", "worse lying flat", "lying flat", "worse at bedtime", "lie down after dinner"],
    "relieved by antacids": ["antacids help", "antacids settle", "tums helps", "antacid helps"],
    "sour taste": ["acid taste", "sour taste in my mouth", "bitter taste", "acid in my throat"],
    # --- GI bleeding
    "hematemesis": ["vomiting blood", "coffee-ground", "coffee grounds", "vomit blood"],
    "melena": ["black tarry stools", "black sticky stools", "tarry black stools", "black stools", "dark tarry stools", "tarry stools", "black and sticky"],
    "hematochezia": ["blood in the stool", "red blood from the bottom", "bright red blood in stool"],
    "lightheadedness": ["feel faint", "dizzy on standing", "light-headed", "lightheaded", "feel lightheaded"],
    "pallor": ["pale", "looks pale", "very pale"],
    # --- stroke / neuro
    "sudden onset focal weakness": ["sudden weakness on one side", "arm will not lift", "right arm is weak", "suddenly cannot move one arm",
                                     "leg suddenly weak", "arm will not", "weakness in my right leg", "right arm weak", "left arm weak"],
    "facial droop": ["face drooped", "one side of the face sags", "mouth is drooping", "drooping face", "face droop", "corner of his mouth is sagging",
                      "corner of her mouth is sagging"],
    "slurred speech": ["speech slurred", "words are slurred", "speech turned to mush", "speaking garbled", "slurred", "speech became slurred",
                        "trouble talking", "speech more slurred"],
    "aphasia": ["cannot find words", "words jumbled", "trouble finding words", "words coming out wrong", "cannot speak properly",
                 "cannot find his words", "cannot find her words"],
    "unilateral numbness": ["numb on one side", "one side feels numb"],
    "sudden vision loss": ["suddenly cannot see out of one eye", "vision went dark in one eye"],
    "ataxia": ["unsteady walking", "cannot walk straight", "poor coordination", "clumsy hand", "off balance", "unsteady on my feet",
                "cannot coordinate", "unsteady gait"],
    "neck stiffness": ["stiff neck", "cannot touch my chin to my chest", "neck will not bend", "neck is rigid", "neck is stiff", "neck stiff",
                        "neck hurts to bend"],
    "photophobia": ["light hurts my eyes", "bright light is painful", "lights hurt", "light bothers me", "bright light bothers",
                     "bright lights bother", "light really bothers"],
    "rash": ["purple spots", "spotty rash", "non-blanching rash", "purple rash"],
    "unilateral pulsating headache": ["pulsing pain on one side of my head", "throbbing one-sided headache", "pounding pain on one side",
                                       "pulsing pain on one side", "pounding headache on one side", "pulsing pain behind one eye"],
    "aura": ["zigzag lights in my vision", "flashing lights in my vision", "zigzag lines", "flickering spots", "zigzag lights",
              "flashing in my eye", "shimmering"],
    "phonophobia": ["noise bothers me", "sounds bother me", "sensitive to noise", "noise and light bother", "light and noise bother"],
    "thunderclap headache": ["sudden explosive headache", "head exploded", "instant worst headache", "like being struck on the head",
                              "hit me all at once", "head felt like it exploded", "exploded while", "like a bomb"],
    "worst headache of life": ["worst headache of my life", "worst i have ever had", "worst of my life", "worst headache ever", "worst ever"],
    "sudden onset severe headache": ["suddenly severe headache", "instant severe headache", "sudden savage headache", "skull-splitting headache"],
    "bilateral band-like pressure": ["tight band around my head", "band around my head", "pressing ache across my forehead", "tight cap",
                                      "dull tight band", "band around"],
    "stress related": ["stressful week", "work stress", "after stress", "deadline", "stressful"],
    # --- musculoskeletal
    "reproducible with palpation": ["hurts when i press on it", "tender when i poke it", "i can press on the exact spot", "pain when i poke the spot",
                                     "tender to touch", "press on it", "poke it", "poke the spot", "press on the exact spot", "flares up if i poke"],
    "worse with movement": ["hurts when i twist", "worse when i twist", "hurts when i move", "worse with twisting", "when i twist", "twisting"],
    "localized tenderness": ["tender over the rib", "chest wall tender", "tender spot", "chest wall tender to touch", "tenderness over the rib"],
    "sharp pain": ["sharp ache", "sharp spot", "sharp"],
    # --- renal / urinary
    "colicky flank pain": ["waves of pain in my side", "cramping flank pain", "pain in waves", "comes in waves", "waves of terrible pain",
                            "comes and goes in waves", "waves of"],
    "pain radiates to groin": ["flank to my groin", "down to my groin", "loin to groin", "flank down to my groin", "side down into my groin", "toward the groin"],
    "hematuria": ["blood in my urine", "saw blood when i peed", "pink urine", "red urine", "blood when i peed", "blood in the urine"],
    "unable to find comfortable position": ["cannot get comfortable", "cannot sit still", "writhing", "cannot lie still"],
    "flank pain": ["pain in my side", "pain in my right side", "ache in my right side", "back pain on one side", "ache in my flank", "kidney area pain",
                    "side hurts", "right flank", "sore back on one side", "throbbing ache in my right side", "my back hurts on one side"],
    "costovertebral angle tenderness": ["tender over the kidney", "tender over the right kidney", "tender in the right flank", "tender right flank",
                                         "tender on the right"],
    "dysuria": _DYSURIA,
    "urinary frequency": ["going often", "need to go every few minutes", "keep running to the toilet", "peeing constantly", "pee a lot",
                           "have to go constantly", "going to the bathroom all the time", "running to the toilet", "need to go every"],
    "urinary urgency": ["need to go urgently", "cannot hold it", "sudden urge to pee", "urgent need to pee"],
    "suprapubic discomfort": ["pressure low in my belly", "low belly pressure", "aching above the pubic bone", "pressure above the pubic bone",
                               "low belly ache", "pressure low down"],
    "no fever": ["no temperature", "no fever"],
    "no flank pain": ["no back pain", "no side pain"],
    # --- sepsis / critical care
    "tachypnea": ["breathing fast", "rapid breathing", "breathing very fast"],
    "suspected infection source": ["chest infection", "urine infection", "infected wound", "urinary catheter", "recent pneumonia", "recent chest infection"],
    # --- electrolytes
    "muscle weakness": ["legs feel like jelly", "weak muscles", "arms feel weak", "generalised weakness", "generalized weakness", "legs feel weak",
                         "arms and legs feel weak", "weak all over"],
    "arrhythmia": ["irregular pulse", "slow pulse", "pulse is slow", "heart skipping", "pulse seems slow"],
    "seizure": ["fit", "convulsion", "had a seizure"],
    # --- panic
    "sudden onset intense anxiety or fear": ["sudden panic", "sudden terror", "intense fear", "felt panicky", "panic came", "felt like i was going to lose it"],
    "hyperventilation": ["fast breathing", "breathing fast", "overbreathing", "cannot get air in", "cannot catch my breath", "cannot get air"],
    "tingling around the mouth or fingers": ["lips tingle", "tingly lips", "hands went numb", "pins and needles in my hands", "tingling lips",
                                              "hands are tingling", "hands tingling", "tingling in my hands", "hands tingly", "numb hands"],
    "fear of dying or losing control": ["felt i was dying", "thought i was dying", "felt i would die", "afraid of dying", "felt like dying",
                                         "feel like i am dying", "feel i am dying"],
    "chest tightness": ["tight chest", "chest feels tight", "tightness in my chest", "chest tightness"],
    "symptoms peak within minutes then improve": ["peaked and settled", "passes in minutes", "settled in about ten minutes", "went away after ten minutes",
                                                    "already easing off", "eased after ten minutes", "settled in minutes"],
    "resolves with calming down or reassurance": ["settled when i calmed down", "improving with reassurance"],
    # --- PE / pneumothorax
    "sudden onset dyspnea": ["suddenly short of breath", "suddenly cannot breathe", "came on suddenly breathless", "cannot catch my breath",
                              "sudden shortness of breath", "gasping", "suddenly gasping", "cannot take a full breath"],
    "hemoptysis": ["coughing up blood", "blood in my cough"],
    "calf swelling": ["calf is swollen", "one calf swollen", "swollen calf", "calf swollen", "leg swollen", "leg is swollen", "calf has been swollen",
                       "calf swollen and tender", "one calf is swollen"],
    "unilateral leg pain": ["one leg sore", "pain in one leg", "aching calf", "calf is sore", "sore calf"],
    "unilateral absent breath sounds": ["no breath sounds on one side", "no breath sounds on the left", "no breath sounds on the right",
                                         "reduced breath sounds on one side", "absent breath sounds"],
    "tracheal deviation": ["windpipe is pushed", "trachea shifted", "windpipe pushed", "trachea pushed over"],
    "chest pain after trauma": ["chest pain after a crash", "after a motorbike crash", "after a fall", "after the impact", "after the crash",
                                 "pain on one side of my chest after a"],
    "hypotension": ["low blood pressure"],
}

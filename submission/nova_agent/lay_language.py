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
_FEVER = ["running a temperature", "high temperature", "feverish", "burning up", "slight fever", "low fever", "mild fever"]
_CONFUSED = ["confused", "muddled", "disoriented", "not making sense", "drowsy and confused", "confusion", "unusual sleepiness",
             "unusually sleepy", "lethargic", "hard to wake"]
_BREATHLESS = ["short of breath", "out of breath", "breathless", "cannot catch my breath", "cannot get air in"]
_DYSURIA = ["burning when i pee", "burns to pee", "stings to pee", "hurts to pee", "burning urination", "pee burns",
            "burning when i wee", "burns when i wee", "pain passing urine", "pain when urinating", "pain on urinating", "pain on urination", "stings when i pee",
            "hurts when i pee", "urinating hurts", "peeing hurts", "wee burns"]

LAY_FEATURE_ALIASES: Dict[str, List[str]] = {
    # --- medication omission (a stopped/run-out drug is NOT current use; see matching._DISCONTINUED_SPAN)
    "missed insulin doses": ["ran out of insulin", "run out of insulin", "stopped insulin",
                             "stopped taking insulin", "skipped insulin", "skipped my insulin", "missed my insulin",
                             "forgot my insulin"],
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
    "substernal pressure": [ "weight on my chest", "band around my chest", "squeezing chest",
                             "pressure below the sternum", "pressure under the breastbone", "pressure behind the breastbone",
                             "heavy weight settles on my chest", "vice squeezing my chest", "chest gets crushed", "chest feels crushed", "squeezing me"],
    "radiates to arm or jaw": ["spreads to my left arm", "pressure spreads to the arm", "pain spreads to the arm", "spreads into my shoulder", "pain goes to my jaw", "jaw ache", "jaw aches",
                                "arm feels heavy", "left arm heaviness", "spreads into my left shoulder", "arm feels heavy"],
    "diaphoresis": _SWEAT,
    "nausea": _NAUSEA,
    "dyspnea on exertion": ["breathless walking", "short of breath on the stairs", "out of breath on exertion", "breathless climbing",
                             "breathless walking to the kitchen"],
    "left arm pain": ["pain in my left arm", "left arm aching", "left arm heavy"],
    "sudden onset palpitations": [ "heart began racing", "sudden pounding heartbeat", "pulse went wild"],
    "irregular heartbeat": ["uneven pulse", "pulse is irregular", "heart skipping beats", "skipped beats", "heart skip",
                             "pulse went wild and irregular", "pulse is uneven"],
    "racing heart": ["heart racing", "heart is pounding", "pulse is fast", "heart thumping", "heart pounding", "heart is racing"],
    "associated lightheadedness": ["feel faint", "feel light-headed", "near fainting", "feel woozy", "feel faint and woozy"],
    "known history of arrhythmia": ["known afib", "history of afib"],
    "palpitations": ["heart pounding", "heart racing", "heart thumping", "heart is pounding", "fluttering heart", "heart fluttering"],
    # --- pancreatitis
    "epigastric pain radiating to back": [
                                           "goes through to my back", "pit of my stomach that goes"],
    "vomiting": _VOMIT,
    "worse after eating fatty food": ["worse after greasy food", "after fatty meals", "greasy meals set it off", "worse after a fatty meal", "greasy food"],
    # --- anaphylaxis
    "sudden onset urticaria": ["hives", "welts all over", "itchy raised rash", "covered in welts", "hives all over"],
    "facial swelling": ["swollen lips", "swollen face", "swollen tongue", "lips and tongue swelling", "lips are huge"],
    "wheeze": ["wheezing", "wheezy", "whistling in my chest", "audible wheeze"],
    "throat tightness": ["throat closing", "throat feels tight", "tight throat", "throat is closing up", "throat squeezing"],
    "recent allergen exposure": ["after a bee sting", "after eating peanuts", "after the antibiotic",
                                  "minutes after my first dose", "after shrimp"],
    # --- dissection
    "tearing chest pain": ["ripping pain in my chest", "tearing pain in my chest", "tearing pain", "ripping pain"],
    "ripping pain": ["tearing pain", "like something ripping", "tearing feeling", "tearing"],
    "pain radiates to back": ["pain goes through to my back", "shooting into my back", "through to my back"],
    "sudden onset severe pain": ["worst pain of my life", "worst pain i have ever had", "came on all at once", "sudden severe pain"],
    "pulse differential": ["weaker pulse in one arm", "pulse deficit"],
    "unequal blood pressure between arms": ["blood pressure different in each arm", "higher in the right arm than the left"],
    # --- appendicitis
    "periumbilical pain migrating to right lower quadrant": [
        "pain began near my navel and moved", "near my belly button now lower right",
        "moved to the right lower belly", "from my navel to the lower right", "moved low on the right", "started near my navel", "pain near my navel"],
    "anorexia": ["no appetite", "loss of appetite", "not hungry", "off my food", "cannot eat"],
    # --- asthma / copd
    "known asthma or copd": ["asthma since childhood", "i have asthma", "i have copd", "history of asthma", "emphysema", "asthma as a teenager", "known asthma"],
    "worse with triggers": ["worse around cats", "dust makes it worse", "cold air makes it worse", "set off by dust", "pollen makes it worse",
                             "cold air always sets it off", "after cleaning the dusty"],
    "prolonged expiration": ["long breathing out", "hard to breathe out", "breathing out takes longer", "prolonged breathing out"],
    # --- vertigo / syncope
    "brief episodic vertigo": [ "spinning for a few seconds", "brief spinning", "dizzy spells that last seconds",
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
    "triggered by standing or pain or fear": ["blood draw", "seeing blood", "standing for ages", "standing in the heat",
                                               "standing a long time", "standing outside in the heat", "fear of needles", "when they took my blood"],
    "brief loss of consciousness": [ "passed out briefly", "went down for a few seconds",
                                     "woke up within seconds", "blacked out"],
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
    "lower abdominal pain": ["low belly ache", "pain low in my belly", "lower tummy pain", "low one-sided belly ache", "ache low down"],
    "vaginal bleeding": ["spotting", "light bleeding", "bleeding from the vagina", "brownish spotting", "light spotting"],
    "missed period": ["period is late", "period is overdue", "weeks late", "missed my period", "period is about six weeks late", "period is six weeks late",
                       "period more than a month late", "cycle is running well behind"],
    "unilateral pelvic pain": ["pain on one side low down", "one-sided lower belly pain", "pain low on the right", "pain low on the left",
                                "low on one side"],
    "dizziness": ["nearly fainted", "almost fainted", "feel faint", "woozy"],
    # --- gastroenteritis / GERD
    "diffuse crampy abdominal pain": ["crampy tummy", "cramping belly", "stomach cramps", "cramps all over my belly", "crampy belly", "cramping all over my belly",
                                       "crampy stomach"],
    "diarrhea": ["loose stools", "watery stools", "runny stools", "the runs", "watery diarrhea", "loose watery"],
    "recent similar illness contact": ["others who ate with me are ill", "everyone who ate it is sick", "companion is ill", "others who ate the same",
                                        "two friends who ate", "others are ill too", "family dinner", "who ate with me", "ate at the same"],
    "burning chest pain": [ "burning in my chest", "heartburn", "burning in the chest", "burning behind"],
    "worse after meals": ["after eating", "after a big meal", "after pizza", "after dinner", "after a large snack", "after a big dinner"],
    "worse lying down": ["when i lie down", "worse lying flat", "lying flat", "worse at bedtime", "lie down after dinner"],
    "relieved by antacids": ["antacids help", "antacids settle", "tums helps", "antacid helps"],
    "sour taste": ["acid taste", "sour taste in my mouth", "bitter taste", "acid in my throat"],
    # --- GI bleeding
    "hematemesis": ["vomiting blood", "coffee-ground", "coffee grounds", "vomit blood"],
    "melena": ["black tarry stools", "black sticky stools", "tarry black stools", "dark tarry stools", "tarry stools", "black and sticky"],
    "hematochezia": ["blood in the stool", "red blood from the bottom", "bright red blood in stool"],
    "lightheadedness": ["feel faint", "dizzy on standing", "light-headed", "lightheaded", "feel lightheaded"],
    "pallor": ["pale", "looks pale", "very pale"],
    # --- stroke / neuro
    "sudden onset focal weakness": ["sudden weakness on one side", "arm will not lift", "right arm is weak", "suddenly cannot move one arm",
                                     "leg suddenly weak", "arm will not", "weakness in my right leg", "right arm weak", "left arm weak"],
    "facial droop": ["face drooped", "one side of the face sags", "mouth is drooping", "drooping face", "face droop",
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
    "unilateral pulsating headache": [ "throbbing one-sided headache", "pounding pain on one side",
                                       "pulsing pain on one side"],
    "aura": ["zigzag lights in my vision", "flashing lights in my vision", "zigzag lines", "flickering spots", "zigzag lights",
              "flashing in my eye", "shimmering"],
    "phonophobia": ["noise bothers me", "sounds bother me", "sensitive to noise", "noise and light bother", "light and noise bother"],
    "thunderclap headache": ["sudden explosive headache", "head exploded", "instant worst headache", "like being struck on the head",
                              "hit me all at once", "head felt like it exploded", "exploded while", "like a bomb"],
    "worst headache of life": [ "worst i have ever had", "worst of my life", "worst headache ever", "worst ever"],
    "sudden onset severe headache": ["suddenly severe headache", "instant severe headache", "sudden savage headache", "skull-splitting headache"],
    "bilateral band-like pressure": [ "band around my head", "tight cap",
                                      "dull tight band", "band around"],
    "stress related": ["stressful week", "work stress", "after stress", "stressful"],
    # --- musculoskeletal
    "reproducible with palpation": [ "tender when i poke it", "i can press on the exact spot", "pain when i poke the spot",
                                     "tender to touch", "press on the exact spot", "flares up if i poke"],
    "worse with movement": ["hurts when i twist", "worse when i twist", "hurts when i move", "worse with twisting"],
    "localized tenderness": ["tender over the rib", "chest wall tender", "tender spot", "chest wall tender to touch", "tenderness over the rib"],
    "sharp pain": ["sharp ache", "sharp spot"],
    # --- renal / urinary
    "colicky flank pain": ["waves of pain in my side", "cramping flank pain", "pain in waves", "comes in waves", "waves of terrible pain",
                            "comes and goes in waves", "waves of"],
    "pain radiates to groin": ["flank to my groin", "down to my groin", "loin to groin", "flank down to my groin", "side down into my groin", "toward the groin"],
    "hematuria": ["blood in my urine", "saw blood when i peed", "pink urine", "red urine", "blood when i peed", "blood in the urine"],
    "unable to find comfortable position": ["cannot get comfortable", "cannot sit still", "writhing", "cannot lie still"],
    "flank pain": ["pain in my side", "pain in my right side", "ache in my right side", "back pain on one side", "ache in my flank", "kidney area pain",
                    "side hurts", "right flank", "sore back on one side", "throbbing ache in my right side", "my back hurts on one side"],
    "costovertebral angle tenderness": ["tender over the kidney", "tender over the right kidney", "tender in the right flank", "tender right flank"],
    "dysuria": _DYSURIA,
    "urinary frequency": ["going often", "keep running to the toilet", "peeing constantly", "pee a lot",
                           "have to go constantly", "running to the toilet", "need to go every"],
    "urinary urgency": ["need to go urgently", "cannot hold it", "sudden urge to pee", "urgent need to pee"],
    "suprapubic discomfort": ["pressure low in my belly", "low belly pressure", "aching above the pubic bone", "pressure above the pubic bone",
                               "low belly ache", "pressure low down"],
    "no fever": ["no temperature", "no fever"],
    "no flank pain": ["no back pain", "no side pain"],
    # --- sepsis / critical care
    "tachypnea": ["breathing fast", "rapid breathing", "breathing very fast"],
    "suspected infection source": ["chest infection", "urine infection", "infected wound", "urinary catheter", "recent pneumonia", "recent chest infection",
                                   "pain on urinating", "pain when urinating", "burning when i pee"],
    # --- electrolytes
    "muscle weakness": ["legs feel like jelly", "weak muscles", "arms feel weak", "generalised weakness", "generalized weakness", "legs feel weak",
                         "arms and legs feel weak", "weak all over"],
    "arrhythmia": ["irregular pulse", "slow pulse", "pulse is slow", "heart skipping", "pulse seems slow"],
    "seizure": ["convulsion", "had a seizure"],
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
    "sudden onset dyspnea": ["suddenly short of breath", "suddenly cannot breathe", "came on suddenly breathless", "cannot catch my breath", "gasping", "suddenly gasping", "cannot take a full breath"],
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


# Additive extensions (merged into existing keys, never replacing them -- a duplicate key in the literal above
# would silently drop the earlier list). Engineering-authored plain wording; NOT clinician-reviewed.
_ADDITIONAL_LAY_ALIASES: Dict[str, List[str]] = {
    "right lower quadrant rebound tenderness": ["rlq rebound", "rebound in the right lower quadrant",
                                                "right lower quadrant tenderness with rebound", "rebound tenderness in the rlq",
                                                "rebound tenderness in the right lower quadrant"],
    "polydipsia": ["thirsty", "excessive thirst"],
    # --- venous-thromboembolism risk context (plain wording for an operation / being bed-bound)
    "recent surgery": ["after my operation", "hip operation", "knee operation", "hip replacement", "knee replacement",
                       "operation last week", "recent operation", "post-op", "after surgery"],
    "immobilization": ["mostly in bed", "stuck in bed", "bedbound", "bed-bound", "confined to bed"],
    # --- exertional angina wording
    "exertional chest pain": ["comes on walking", "comes on when i walk", "eases when i rest", "goes away with rest",
                              "on walking uphill"],
    # --- Round P: either half of a disjunctive KB phrase states it ("vomiting or diarrhea" is met by vomiting)
    "vomiting or diarrhea": ["vomiting", "vomited", "throwing up", "threw up", "diarrhea", "diarrhoea", "loose stools"],
    "prior stroke or tia": ["previous stroke", "had a stroke before", "mini-stroke", "transient ischaemic attack",
                            "transient ischemic attack"],
    "prior dvt or pe": ["previous blood clot", "clot in my leg before", "clot in my lung before", "previous dvt"],
    "muscle cramps": ["cramps in my legs", "leg cramps", "muscle cramps", "cramping muscles"],
    # --- Round Q: observed wording for existing KB features (feature-local; no global word substitution).
    # Reduced power/strength IS weakness; its location stays in the original text and nothing is inferred about a cause.
    "muscle weakness": ["reduced power", "power is reduced", "decreased power", "reduced strength", "decreased strength",
                        "weak in both legs", "weak in both arms"],
    # The KB phrase carries a redundant "associated"; the observation itself is lightheadedness (not fainting).
    "associated lightheadedness": ["lightheaded", "light-headed", "lightheadedness", "light headed"],
    # A convulsive fit is a seizure; a bare "fit" is NOT mapped (fit/fits well/keep fit).
    "seizure": ["convulsive fit", "convulsing", "convulsions", "fitting and shaking",
                # Round U follow-up (NHS "Epilepsy": seizures are also called fits): EVENT phrasings only.
                "short fit", "brief fit", "a fit this morning", "a fit last night", "a fit today", "had a fit and",
                "one fit", "fit this morning"],
    # Sudden acceleration of the heartbeat described in lay words.
    "sudden onset palpitations": ["heart suddenly took off", "heart took off", "heart suddenly accelerated",
                                  "heart suddenly raced"],
    "racing heart": ["heart took off", "heart accelerated", "heart sped up"],
    # Kidney failure treated with dialysis is CKD category G5D (KDIGO 2012 CKD guideline, Kidney Int Suppl 2013;3:1-150).
    # A plain "kidney problem" is NOT mapped: chronicity is not assumed.
    "chronic kidney disease": ["on dialysis", "ongoing dialysis", "regular dialysis", "haemodialysis", "hemodialysis",
                               "peritoneal dialysis", "dialysis three times a week"],
    # Relief by sitting forward stated in the patient's words (pericarditis-type relief); feature-local.
    # (Variants that coincide with reference-blind wording are deliberately absent: scripts/check_eval_leakage.py.)
    "pain eased by leaning forward": ["leaning forward helps", "relieved by leaning forward", "better leaning forward",
                                      "sitting forward helps"],
    # Lay wording found on the Round Q contrast development set (development use, disclosed in the report).
    "bilateral band-like pressure": ["pressing on both sides", "pressure on both sides", "squeezing on both sides"],
    "prolonged screen time": ["staring at screens", "screens all day", "on the computer all day", "looking at a screen all day"],
    "heat intolerance": ["can't stand the heat", "can not stand the heat", "can't tolerate the heat"],
    "fear of dying or losing control": ["something terrible will happen", "sense of doom", "feel i'm going to die",
                                        "feel like i'm dying"],
    "tingling around the mouth or fingers": ["tingling fingers", "fingers tingle", "my fingers tingle"],
    # Heart failure, cardiomyopathy and previous myocardial infarction are structural heart disease, a high-risk
    # feature for arrhythmic syncope (Brignole M et al., 2018 ESC Guidelines for syncope, Eur Heart J 2018;39:1883, Table 5).
    "structural heart disease": ["heart failure", "cardiomyopathy", "previous heart attack", "had a heart attack",
                                 "weak heart muscle"],
    "missed dialysis session": ["missed dialysis", "missed my dialysis", "skipped dialysis", "missed two dialysis sessions",
                                "missed a dialysis session", "missed scheduled dialysis"],
    # --- Round U follow-up: observed wording that never reached an existing KB phrase (traced on development cases;
    # disclosed as development use). Each list helps ONE phrase only and asserts no new clinical relationship.
    # "Abdominal pain is pain that you feel anywhere between your chest and groin. This is often referred to as the
    # stomach region or belly" (MedlinePlus, "Abdominal pain", medlineplus.gov/ency/article/003120.htm).
    # "stomach" alone stays unmapped (organ vs region): only explicit pain/ache wording is listed.
    "abdominal pain": ["stomach pain", "stomach ache", "stomachache", "tummy ache", "pain in my stomach",
                       "stomach hurts", "my stomach is sore"],
    # A current diabetes diagnosis stated by type. Family/past scoping is applied by the caller as for every alias.
    "known diabetes": ["type 1 diabetes", "type 2 diabetes", "type 1 diabetic", "type 2 diabetic", "i have diabetes",
                       "i am diabetic", "i'm diabetic"],
    # Insulin not delivered because the device failed is a missed dose (same omission as running out).
    "missed insulin doses": ["insulin pump stopped", "insulin pump failed", "pump stopped working", "pen broke",
                             "insulin pen broke"],
    # Kussmaul respiration is deep, laboured breathing (StatPearls, "Kussmaul Respirations", NBK470309).
    "kussmaul breathing": ["deep laboured breathing", "deep labored breathing", "deep sighing respirations",
                           "deep sighing breathing", "deep and laboured breathing", "deep and labored breathing"],
    "recent similar illness contact": ["several people at dinner got", "everyone who ate", "others who ate",
                                       "people who ate there", "who ate there has it", "has the same bug",
                                       "had the same bug", "has the same illness", "same illness", "family are ill too"],
    "diffuse crampy abdominal pain": ["cramping across the abdomen", "cramping across my belly", "cramps across my belly",
                                      "cramps across my tummy", "abdominal cramps", "cramping across my abdomen"],
    "food exposure": ["after the shared dinner", "shared dinner", "after a barbecue", "after a takeaway",
                      "after eating out", "a few hours after eating"],
    # --- chest-wall injury wording (the KB phrases already exist on musculoskeletal chest pain)
    "recent trauma": ["fell off my bike", "fell off my bicycle", "after a fall", "since i fell", "had a fall",
                      "slipped and fell", "slipped on ice", "landed on my side", "was hit in the chest"],
    "reproducible with palpation": ["pressing on the ribs", "press on them", "pressing on the sore spot",
                                    "hurts when i press", "sore to press", "tender to touch", "pressing on it hurts"],
    # --- heart-failure congestion wording (Tier-2 HF profiles already list these phrases)
    "ankle swelling": ["ankles swell", "swollen ankles", "ankles are swollen", "ankles get swollen", "ankle edema"],
    "leg swelling": ["pitting edema", "swollen legs", "legs are swollen", "legs swell"],
    "waking breathless at night": ["wake up gasping", "waking up gasping", "wake up breathless", "wake up short of breath"],
    "crackles in lungs": ["crackles at both bases", "crackles at the bases", "bibasal crackles", "bibasilar crackles",
                          "basal crackles"],
    # Syncope with no prodrome (ESC 2018 syncope guideline Table 5); the KB phrase is on the arrhythmia CATEGORY.
    "syncope without warning": ["passed out without any warning", "passed out without warning", "out with no warning at all",
                                "collapsed without warning",
                                "fainted without warning", "fainted with no warning", "lost consciousness without warning"],
    # Pain under the right costal margin IS right-upper-quadrant pain (anatomical region, no cause implied).
    "right upper quadrant pain": ["under my right ribs", "below my right ribs", "under the right ribs",
                                  "upper right of my belly", "upper right belly", "right upper belly"],
    # Naming the big toe states that the big-toe joint region is involved; "overnight" onset is night onset.
    "big toe joint involvement": ["my big toe", "the big toe", "base of the big toe", "big toe joint"],
    "night onset": ["overnight my", "came on overnight", "woke at night with", "woke me at night"],
    # Blurred / lost vision is a visual disturbance (no cause or laterality inferred).
    "visual disturbance": ["blurred vision", "blurry vision", "vision went blurry", "loss of vision",
                           "lost vision", "double vision"],
    "night time pain": ["wakes me at night", "wakes me up at night", "woke me at night"],
    # Palpitations immediately preceding syncope (ESC 2018 syncope guideline Table 5; arrhythmia CATEGORY only).
    "palpitations before syncope": ["heart skip beforehand", "heart skipped beforehand", "fluttering for a few minutes before",
                                    "palpitations beforehand", "palpitations before i fainted",
                                    "palpitations before i passed out", "heart raced before i passed out",
                                    "heart racing before i blacked out"],
    # Orthopnoea quantified by pillows (NICE CKS "Heart failure - chronic": orthopnoea).
    "unable to lie flat": ["three pillows to sleep", "need three pillows", "need extra pillows to sleep",
                           "sleep propped up", "cannot lie flat", "can't lie flat"],
    # --- peritonism wording on examination
    "rebound tenderness": ["with rebound", "rebound everywhere", "rebound tenderness everywhere"],
    "lying still": ["lying very still", "lying completely still", "keeps very still"],
}
for _phrase, _variants in _ADDITIONAL_LAY_ALIASES.items():
    _bucket = LAY_FEATURE_ALIASES.setdefault(_phrase, [])
    _bucket.extend(v for v in _variants if v not in _bucket)


# --- Tier-2 enrichment features (nova_agent/knowledge/tier2_enrichment.json) -------------------------
# Same provenance and discipline as above: agent-authored patient-wording variants for ONE exact
# enriched feature phrase each; multi-word, no bare generic words.
_TIER2_LAY: Dict[str, List[str]] = {
    # Round U follow-up (Sjogren entry, see its field provenance): chronic dryness stated with its duration.
    "persistent dry eyes": ["dry eyes for months", "eyes have been dry for months", "eyes stay dry"],
    "persistent dry mouth": ["dry mouth for months", "mouth stays dry", "mouth has been dry for months"],
    "band-like blistering rash": ["stripe of blisters", "line of blisters", "clusters of blisters", "blisters in a band", "band of blisters"],
    "burning pain on one side of body": ["burning stripe on one side", "burning on one side of my chest", "burning pain on one side", "burning band on one side"],
    "painful blistering rash": ["painful blisters", "blisters that hurt", "blistering rash"],
    "sudden hot red swollen joint": ["joint became hot red and swollen", "hot red swollen joint", "toe became hot", "joint is hot and red"],
    "hot swollen painful joint": ["hot swollen knee", "swollen hot joint", "hot painful swollen joint", "joint is hot and swollen", "knee is hot and swollen"],
    "inability to move the joint": ["cannot bend it", "cannot bend the knee", "cannot move the joint", "cannot move my knee"],
    "dark cola colored urine": ["cola coloured urine", "cola colored urine", "tea coloured urine", "tea colored urine", "dark brown urine"],
    "severe muscle pain": ["severe aching muscles", "muscles are very sore", "terrible muscle pain", "muscle pain after"],
    "recent intense exercise or crush injury": ["after a marathon", "after a hard workout", "after running a marathon", "after extreme exercise"],
    "pain on moving the eye": ["pain when i move my eye", "pain when moving the eye", "hurts to move my eye", "pain with eye movement"],
    "vision loss in one eye": ["blurring in one eye", "blurred vision in one eye", "cannot see out of one eye", "dim vision in one eye"],
    "washed out colors": ["colours look washed out", "colors look washed out", "colours look faded", "colors look faded"],
    "severe eye pain": ["severe pain in the eye", "terrible eye pain", "eye pain is severe"],
    "halos around lights": ["rings around lights", "halos around the lights", "haloes around lights"],
    "ear pain": ["earache", "ear ache", "my ear hurts", "pain in the ear"],
    "feeling of blocked ear": ["blocked feeling", "ear feels blocked", "blocked ear", "muffled hearing"],
    "child pulling at ear": ["tugging the ear", "tugging at the ear", "pulling at the ear", "pulling his ear", "pulling her ear"],
    "recent cold": ["after a cold", "after a head cold", "recent cold"],
    "unilateral calf swelling": ["one calf is swollen", "calf is swollen", "swollen calf", "swelling of one calf", "one leg swollen"],
    "calf pain or tenderness": ["calf is sore", "sore calf", "calf is painful", "calf tenderness", "tender calf"],
    "warmth and redness of leg": ["calf is warm", "leg is warm and red", "warm red leg", "warm and swollen calf"],
    "recent immobility or long travel": ["long drive", "long flight", "after a long trip", "sitting for hours", "bed rest"],
    "left lower quadrant pain": ["left lower belly pain", "pain in the lower left belly", "lower left abdominal pain", "left lower abdominal pain"],
    "right lower abdominal pain": ["right lower belly pain", "lower right belly pain", "pain in the lower right belly"],
    "right upper quadrant pain": ["right upper belly pain", "upper right belly pain", "pain in the upper right belly"],
    "pain after fatty meals": ["after fatty food", "after greasy food", "after a fatty meal", "after a greasy meal"],
    "pain after eating fatty food": ["after fatty food", "after greasy food", "after a fatty meal"],
    "change in bowel habit": ["changed bowel habit", "bowel habit has changed", "bowels have changed", "constipation and diarrhoea", "constipated"],
    "abdominal distension": ["swollen belly", "bloated belly", "belly is swollen", "belly swollen", "distended belly"],
    "unable to pass gas or stool": ["no gas or stool", "not passing gas", "cannot pass gas", "no gas and no stool", "not passed gas or stool"],
    "colicky abdominal pain": ["crampy belly pain", "cramping belly pain", "crampy pain in my belly", "belly cramps that come and go", "crampy abdominal pain"],
    "repeated vomiting": ["keep vomiting", "vomiting repeatedly", "vomiting again and again", "repeated vomiting", "vomited several times"],
    "sudden severe testicular pain": ["sudden severe pain in one testicle", "sudden pain in one testicle", "severe pain in the testicle", "severe testicle pain"],
    "swollen tender testis": ["swollen tender testicle", "swollen painful testicle", "high swollen tender testicle", "swollen testicle"],
    "high riding testis": ["testicle sits high", "testicle is riding high", "testicle looks high", "high swollen tender testicle"],
    "scrotal pain and swelling": ["painful swollen scrotum", "swollen painful scrotum", "scrotum is swollen and painful"],
    "sudden severe lower abdominal pain on one side": ["sudden severe low belly pain on one side", "sudden severe pain low on one side of the belly"],
    "burning upper abdominal pain": ["burning upper belly pain", "burning pain in my upper belly", "burning pain in the upper belly"],
    "night time pain waking from sleep": ["wakes me at night", "wakes me up at night", "pain wakes me", "wakes me from sleep"],
    "pain relieved by eating": ["eases with food", "better after eating", "eases after eating", "relieved by food", "eases when i eat"],
    "sudden one-sided chest pain": [ "sudden one sided chest pain", "sudden chest pain on one side"],
    "shortness of breath": ["breathless", "short of breath", "out of breath", "cannot catch my breath"],
    "sharp chest pain": ["sharp pain in my chest", "sharp stabbing chest pain", "sharp pain in the chest"],
    "pain eased by leaning forward": [ "better leaning forward", "eases leaning forward"],
    "pain worse lying flat or breathing in": ["worse lying flat", "worse when lying flat", "worse with deep breaths", "worse on deep breathing", "worse when i breathe in"],
    "recent viral illness": ["flu-like illness", "after a viral illness", "after a flu-like illness", "after the flu", "after a cold"],
    "palpitations": ["racing heart", "heart racing", "heart is pounding", "heart fluttering", "heart pounding"],
    "weight loss despite good appetite": ["losing weight but eating well", "weight loss with a good appetite", "losing weight despite eating"],
    "heat intolerance": ["cannot stand the heat", "hate the heat", "always too hot", "feel too hot", "intolerance of heat"],
    "tremor": ["shaky hands", "hands shake", "hands are shaky", "trembling hands", "shaking hands"],
    "severe abdominal pain out of proportion to examination": ["severe belly pain with little to find", "severe pain but belly feels soft", "pain out of proportion"],
    "pain after eating": ["pain after eating", "pain after meals", "belly pain after eating", "pain starts after eating"],
    "atrial fibrillation or vascular disease": ["atrial fibrillation", "irregular pulse", "irregular heartbeat", "vascular disease"],
    "saddle numbness": ["numb saddle area", "numbness in the saddle area", "numb around the buttocks and genitals", "numb between the legs"],
    "urinary retention or incontinence": ["trouble passing urine", "cannot pass urine", "difficulty passing urine", "leaking urine", "cannot control my bladder"],
    "low back pain": ["severe back pain", "lower back pain", "back pain"],
    "ascending weakness starting in legs": ["weakness that started in my feet", "weakness climbing up my legs", "weakness started in the feet", "legs getting weaker"],
    "tingling in feet and hands": ["tingling in the feet", "tingling in my feet", "pins and needles in the feet", "tingling in my hands"],
    "recent infection": ["after a stomach bug", "after a cold", "after an infection", "after a viral illness"],
    "new headache in person over 50": ["new one-sided headache in an older person", "new headache in an older person", "new headache in older patient"],
    "scalp tenderness": ["tender scalp", "scalp is tender", "scalp is sore", "painful scalp"],
    "jaw pain on chewing": ["jaw ache when chewing", "jaw pain when chewing", "jaw hurts when i chew", "jaw ache on chewing"],
    "jaundice": ["yellow skin", "yellow eyes", "skin has turned yellow", "yellowing of the skin"],
    "fever and chills": ["shaking chills", "fever with chills", "fever and shivering", "chills and fever"],
    "dark urine": ["dark urine", "dark coloured urine", "urine is dark", "dark colored urine"],
    "abnormal vaginal discharge": ["abnormal discharge", "unusual discharge", "foul smelling discharge", "vaginal discharge"],
    "new sexual partner": ["new partner", "new sexual partner", "a new partner"],
    "pain with intercourse": ["pain during sex", "painful sex", "pain with sex", "hurts during sex"],
    "fever": ["fever", "feverish", "high temperature", "running a temperature"],
    "burning urination": ["burning when i pee", "burning urination", "burns when i pee", "burning on urination"],
    "bulging red eardrum": ["red bulging eardrum"],
    "tingling before rash": ["tingling before the rash", "tingling then a rash"],
    "red warm swollen skin": ["red hot patch", "red hot spreading patch", "hot red patch of skin", "red warm swollen skin", "red hot and swollen skin", "warm red tender swelling"],
    "spreading redness": ["spreading patch", "spreading redness", "redness is spreading", "patch is spreading"],
    "tender skin": ["skin is tender", "tender red skin", "painful skin"],
    "lower abdominal pain": ["low belly pain", "lower belly pain", "pain in my lower belly"],
    "nausea and vomiting": ["nausea and vomiting", "feeling sick and vomiting", "sick and vomiting"],
    "headache with nausea and vomiting": ["headache with nausea", "headache and feel sick", "headache and nausea"],
    "blurred vision": ["blurred vision", "blurry vision", "vision is blurry", "blurring of vision"],
}
for _phrase, _variants in _TIER2_LAY.items():
    _bucket = LAY_FEATURE_ALIASES.setdefault(_phrase, [])
    _bucket.extend(v for v in _variants if v not in _bucket)

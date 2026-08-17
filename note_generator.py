"""Builds BCBA session notes and caregiver training notes from clicked selections.

Output is flowing narrative paragraphs (no bullet/label formatting), with randomized
phrasing so that two notes built from identical selections do not read as near-duplicates.
"""
import json
import os
import random
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OPTIONS_PATH = os.path.join(BASE_DIR, "default_options.json")

TARGET_LOW = 700
TARGET_HIGH = 800

CONNECTORS = [
    "Additionally, ", "During the session, ", "As part of programming, ", "At the same time, ", "Alongside this, ",
    "Later in the session, ", "From there, ", "Building on this, ", "In the same vein, ", "By comparison, ", "",
]

SESSION_INTRO_TEMPLATES = [
    "{bcba} actively observed and guided {rbt} throughout today's {duration}direct ABA therapy session for {name} at {place}, ensuring the session was carried out in accordance with the designed protocol and {name}'s current treatment plan.",
    "During today's {duration}direct ABA therapy session for {name} at {place}, {bcba} actively observed {rbt} and provided real-time guidance to ensure implementation followed the protocol as designed.",
    "{bcba} was actively engaged in observing and guiding {rbt} throughout today's {duration}direct ABA therapy session for {name} at {place}, ensuring adherence to the designed treatment protocol and behavior intervention plan.",
    "Throughout today's {duration}direct ABA therapy session for {name} at {place}, {bcba} actively observed and guided {rbt} to ensure the session was implemented in accordance with the designed protocol plan.",
]

RBT_SESSION_INTRO_TEMPLATES = [
    "This note documents a {duration}direct ABA therapy session for {name} conducted by {rbt} at {place}, in accordance with {name}'s current treatment plan and behavior intervention plan.",
    "{rbt} conducted a {duration}direct ABA therapy session for {name} at {place}, following the goals and procedures outlined in {name}'s current treatment plan.",
    "{name} was seen for a {duration}direct ABA therapy session at {place}, conducted by {rbt} in accordance with the treatment plan and behavior intervention plan designed by the treating BCBA.",
    "{rbt} provided a {duration}direct ABA therapy session for {name} at {place}, implementing programming as outlined in the current treatment plan.",
]

SESSION_PROGRAMS_LEAD = [
    "During today's session, programming focused on several skill acquisition targets.",
    "The session included structured programming across a number of skill acquisition goals.",
    "Skill acquisition programming was a central focus of today's session.",
    "Today's session incorporated targeted instruction across the client's current skill acquisition goals.",
]

SESSION_PROGRAMS_CLOSE = [
    "Overall, programming targeted {labels}, with prompting and reinforcement provided as needed to support acquisition.",
    "Across these areas ({labels}), prompts were faded where appropriate and reinforcement was delivered contingent on correct or approximated responses.",
    "Instruction in {labels} was supported through individualized prompting and a reinforcement schedule matched to the client's current level.",
    "The client's responses across {labels} were reinforced and shaped toward the current mastery criteria for each program.",
]

SESSION_BEHAVIOR_LEAD = [
    "The session also involved addressing behaviors of clinical concern.",
    "Behavioral concerns were observed and addressed throughout the session.",
    "In addition to skill acquisition, the session addressed target behaviors identified on the behavior intervention plan.",
    "The client's behavior was monitored throughout the session, with the following concerns noted.",
]

INTERVENTION_EFFECTIVENESS_TEMPLATES = [
    "This intervention {blurb}.",
    "Overall, the intervention {blurb}.",
    "Across the session, this approach {blurb}.",
]

ENVIRONMENTAL_CHANGE_TEMPLATES = [
    "The following environmental changes were noted prior to the session: {changes}.",
    "Prior to the session, the following environmental changes were reported: {changes}.",
    "The following changes in the client's environment were noted going into today's session: {changes}.",
]

MEDICAL_CONCERN_TEMPLATES = [
    "The following medical concerns were noted prior to the session: {concerns}.",
    "Prior to the session, the following medical concerns were reported: {concerns}.",
    "The following medical factors were noted going into today's session: {concerns}.",
]

BCBA_REVIEW_LEAD = [
    "{bcba_name} conducted a direct observation of today's session ({method}).",
    "As part of ongoing quality assurance, {bcba_name} directly observed today's session ({method}).",
    "{bcba_name} completed a direct observation of the RBT's implementation of today's session ({method}).",
    "Today's session was directly observed by {bcba_name} ({method}).",
]

BCBA_REVIEW_RATING_TEMPLATES = [
    "The RBT's implementation of the protocol was rated as {rating}.",
    "Overall protocol implementation was rated {rating}.",
    "The {reviewer} rated today's implementation as {rating}.",
]

BCBA_REVIEW_STRENGTHS_TEMPLATES = [
    "Noted strengths included {strengths}.",
    "Areas of strong performance included {strengths}.",
    "The RBT demonstrated particular strength in {strengths}.",
]

BCBA_REVIEW_FEEDBACK_TEMPLATES = [
    "The following feedback and direction were provided to the RBT to guide continued implementation of the protocol: {feedback}.",
    "To support continued growth, the {reviewer} provided direction on {feedback}.",
    "The RBT was given specific feedback and direction regarding {feedback}.",
]

SESSION_DATA_TEMPLATES = [
    "Data on target programs and behaviors were collected using {methods}. Collected data were reviewed to evaluate progress toward mastery criteria and to inform any adjustments to the treatment plan.",
    "{methods_cap} were used to track progress throughout the session. This information was reviewed to assess trends relevant to both skill acquisition and behavior reduction goals.",
    "Progress was tracked using {methods}, and the resulting data were reviewed to determine whether current programming and intervention strategies remain appropriate.",
    "Throughout the session, {methods} were used to document performance, and this information will be incorporated into the client's ongoing progress record.",
]

SESSION_SUMMARY_LEAD = [
    "Looking at the session as a whole, ",
    "In summary, ",
    "Taken together, today's session showed that ",
    "Overall, ",
]

SESSION_FILLERS = [
    "Reinforcement was delivered on a schedule matched to the client's current level of skill acquisition.",
    "Staff adjusted pacing in real time as the client's rate of responding shifted across the session.",
    "Ongoing progress will continue to be monitored across sessions, with adjustments made to the treatment plan as needed.",
    "Today's data were reviewed with an eye toward trends relevant to mastery criteria and behavior reduction goals.",
    "Preferred items rotated through the session kept reinforcement effective without over-relying on any single one.",
    "Overall, the client's responding tracked closely with patterns seen in recent sessions.",
    "Seating and materials were arranged ahead of time to keep the client oriented to the task at hand.",
    "Protocol steps were followed as written throughout the session.",
    "Generalization across materials, prompts, and settings remains a standing focus of programming going forward.",
    "Today's session followed the goals laid out in the client's individualized treatment plan.",
    "Staff continue to loop in caregivers to keep strategies consistent across home and session.",
    "This session's findings will roll into the client's ongoing progress summary.",
    "Rotating materials throughout the session helped keep reinforcement from losing its effect.",
    "Prompts were faded and reintroduced as needed depending on how the client responded trial to trial.",
    "A couple of short movement breaks were worked into the session to head off problem behavior before it started.",
    "The client moved between activities with varying levels of support; transition cues signaled each change ahead of time.",
    "The first few minutes were spent building rapport before moving into structured programming.",
    "Antecedent strategies were put in place proactively rather than reactively.",
    "Task difficulty shifted slightly over the course of the session to keep responding consistent.",
    "A quick informal preference check at the start of the session shaped which items were used for reinforcement.",
    "Staff checked in on the client's schedule and any changes at home or school before starting programming.",
    "Prior session notes were reviewed beforehand to keep programming and strategies consistent.",
    "Performance across today's programs was documented to inform planning for the next session.",
    "The session mixed structured trials with more naturalistic teaching opportunities.",
    "Where applicable, token systems were checked in on with the client at a few natural points in the session.",
    "Both rate of responding and occurrence of target behaviors were tracked alongside formal data collection.",
    "Staff will keep coordinating with the rest of the care team to keep strategies consistent across settings.",
    "Nothing safety-relevant came up during the session that would need separate follow-up.",
    "The treatment plan and behavior intervention plan remain under periodic review to confirm goals are still appropriate.",
    "Today's session adds to the broader dataset used to track the client's trajectory over time.",
    "Responding across today's programs and behaviors fell in line with what's expected at this stage of treatment.",
    "Staff kept building rapport with the client throughout, which supported responding during more demanding tasks.",
    "Reinforcer variety was kept up across the session to avoid satiation on any one item.",
    "Materials were staged in advance so transitions between programs stayed efficient.",
    "Progress across today's targeted programs and behaviors will be folded into the client's ongoing treatment record.",
    "The client was offered small choices throughout the session, such as which material to use first.",
    "Wherever possible, today's session mirrored the structure of recent sessions to support consistency.",
    "The physical space was cleared ahead of time to cut down on clutter and distraction.",
    "A short check-in at the start of the session covered anything relevant that had come up since last time.",
    "Short breaks were offered between more demanding tasks to help the client maintain a steady pace.",
    "Instructions stayed short and direct throughout, which supported correct responding.",
    "The order of activities shifted partway through based on how the client was responding.",
    "The last few minutes of the session were used to recap progress with the client.",
    "Today's activity choices took the client's current preferences into account.",
    "Verbal praise was consistently paired with tangible reinforcement to strengthen the client's responses.",
    "The client had a few built-in opportunities to choose between two or more activities during the session.",
    "Staff checked responding periodically before moving on to the next task in the sequence.",
    "A visual timer helped cue the client ahead of upcoming transitions at a few points in the session.",
    "Comparing the start and end of the session, response rate held steady.",
    "New materials were introduced gradually, with response rates tracked closely as each was added.",
    "Easier and harder tasks were interspersed to keep the client's rate of correct responding consistent.",
    "Staff stayed nearby during less structured portions of the session as a safety precaution.",
    "The client's communication attempts, both verbal and nonverbal, were acknowledged and reinforced throughout.",
    "A brief cool-down activity closed out the session to support an orderly transition.",
    "Running the session in a quieter area helped cut down on outside distractions during structured tasks.",
    "Staff kept instruction wording consistent across the session to reduce errors in responding.",
    "One movement break was built into the middle of the session to support continued participation.",
    "Trial-to-trial variability in responding was noted and factored into pacing decisions as the session went on.",
    "By the session's end, the client had moved through each targeted program at least once.",
    "Staff paired brief verbal feedback with reinforcement to clarify which responses were correct.",
]

CAREGIVER_INTRO_TEMPLATES = [
    "This note documents a {duration}caregiver training session for {name}, provided to {caregiver} at {place}. The session was conducted by {provider} with the goal of increasing the caregiver's capacity to implement behavior-analytic strategies across natural environments.",
    "{caregiver} participated in a {duration}caregiver training session focused on {name}'s treatment goals, held at {place} and led by {provider}. The session aimed to build the caregiver's skills in applying behavior-analytic strategies at home.",
    "{provider} met with {caregiver} for a {duration}caregiver training session related to {name}'s care, conducted at {place}. The session supported the caregiver's ongoing ability to carry out strategies across settings.",
    "A {duration}caregiver training session was held at {place} for {caregiver}, caregiver of {name}, facilitated by {provider} to strengthen consistent implementation of strategies outside of scheduled sessions.",
]

CAREGIVER_TOPICS_LEAD = [
    "Today's training covered several key areas relevant to {name}'s current treatment plan.",
    "The session addressed multiple training topics tied to {name}'s ongoing goals.",
    "Training content today was drawn directly from {name}'s treatment plan and current areas of need.",
    "The following topics were covered during today's caregiver training session.",
]

CAREGIVER_METHOD_TEMPLATES = [
    "Content was delivered using {methods} to support the caregiver's understanding and skill development.",
    "{methods_cap} were used throughout the session to reinforce the material covered.",
    "The BCBA used {methods} to walk through each topic and check for understanding.",
    "Training relied on {methods}, allowing the caregiver opportunities to engage with the material directly.",
]

CAREGIVER_FILLERS = [
    "The caregiver was encouraged to reach out between sessions with any questions about implementing the strategies discussed.",
    "Written and verbal instructions were provided to support the caregiver's recall and application of today's training content.",
    "The BCBA emphasized the importance of consistency across caregivers and settings to support the client's overall progress.",
    "Opportunities for the caregiver to practice the discussed strategies were provided during the session, with feedback given in real time.",
    "The caregiver's current level of implementation will continue to be assessed and supported across upcoming training sessions.",
    "Training content was individualized to align with the client's current treatment goals and the family's daily routines.",
    "The caregiver was given the opportunity to ask questions and share observations regarding the client's behavior at home.",
    "Follow-up will occur during the next scheduled caregiver training session to review progress and address any ongoing concerns.",
    "The BCBA acknowledged the caregiver's efforts and provided constructive feedback to support continued skill development.",
    "Strategies discussed today were selected to be feasible within the family's typical routines and available resources.",
    "Examples specific to the client's daily routine were used to illustrate how each strategy could be applied at home.",
    "The caregiver was asked to describe recent situations at home so that strategies could be tied to real examples.",
    "A brief review of data or observations from the prior week informed which topics were prioritized during today's session.",
    "The BCBA modeled key strategies during the session before inviting the caregiver to practice them directly.",
    "Handout materials summarizing today's content were reviewed with the caregiver for use as an at-home reference.",
    "The caregiver's questions were addressed throughout the session, with additional clarification provided as needed.",
    "Today's session built on strategies introduced during previous caregiver training sessions.",
    "The importance of pairing reinforcement with newly taught strategies was discussed as part of today's training.",
    "The BCBA and caregiver discussed how to track progress informally between scheduled sessions.",
    "Plans for coordinating strategies with other caregivers in the home were discussed briefly during the session.",
    "The caregiver was encouraged to start with small, manageable changes rather than attempting to implement every strategy at once.",
    "Today's training was tailored to fit within the family's current schedule and daily demands.",
    "The BCBA checked in on how previously discussed strategies have been working at home before introducing new content.",
    "Realistic expectations for progress were discussed, along with the importance of consistency over time.",
    "The caregiver practiced the strategies discussed during the session, with feedback provided in real time.",
    "Next steps for continued training and support were outlined collaboratively with the caregiver.",
    "The caregiver was encouraged to keep a brief log of attempts to use the strategies at home so progress can be reviewed together.",
    "Visual reminders and simple cues were discussed as a way to support consistent use of the strategies between sessions.",
    "The BCBA and caregiver discussed how to involve other family members in the home so that strategies are applied consistently.",
    "Recent successes reported by the caregiver were highlighted to reinforce continued use of the strategies at home.",
    "The BCBA and caregiver discussed how to respond consistently, using planned strategies rather than reactive responses, on days when the client's behavior is more difficult to manage.",
    "Coordination with the client's school or daycare team was discussed as a way to support consistency of strategies across settings.",
    "The caregiver was reassured that setbacks are a normal part of the process and do not undo prior progress.",
    "Environmental adjustments at home, such as arranging materials or seating, were discussed as a way to support the strategies covered today.",
    "The BCBA reviewed how to pair verbal praise with other forms of reinforcement to strengthen the caregiver's use of the strategies.",
    "Today's session concluded with a brief recap of the key points covered to support the caregiver's retention of the material.",
    "The caregiver's current strengths in implementing prior strategies were acknowledged before introducing additional content.",
    "The BCBA and caregiver reviewed which strategies were most consistently implemented to prioritize heading into the coming week.",
    "The physical layout of the home was briefly discussed to identify spots that could reduce problem behavior during transitions.",
    "The caregiver shared how mealtimes and bedtime routines typically unfold, which helped shape today's recommendations.",
    "A short demonstration was used to show how prompting can be faded gradually as the client gains independence.",
    "The BCBA and caregiver talked through a recent outing to identify what worked well and what could be adjusted.",
    "Ideas for keeping siblings included in a positive way were discussed without disrupting the client's programming.",
    "The caregiver mentioned specific times of day that tend to be more difficult, which helped focus today's planning.",
    "A simple checklist was suggested as a way to keep track of which strategies have been tried during the week.",
    "The BCBA walked through how to respond if a strategy does not work right away, to avoid abandoning it too soon.",
    "The caregiver was invited to share which strategies have been implemented consistently so far and which have been harder to keep up with.",
    "Today's discussion touched on how errands and outings in the community can be planned with the client's needs in mind.",
    "The BCBA offered suggestions for adapting today's strategies for use during holidays or changes to the usual schedule.",
    "The caregiver and BCBA discussed how extended family members might be briefly introduced to the strategies being used.",
    "A few common questions from other caregivers were shared as examples of concerns that often come up early in training.",
    "The caregiver was reminded that progress at home often looks different from progress during a formal session.",
    "The BCBA suggested keeping reinforcement items varied at home to reduce the likelihood of satiation over time.",
    "Today's conversation included a brief check on how the client has been sleeping, since this can affect behavior during the day.",
    "The caregiver asked about handling situations in public, and a few simple options were discussed for those moments.",
    "The BCBA noted that today's strategies can be adjusted further as the caregiver gains more practice using them.",
    "A short list of warning signs was reviewed so the caregiver can recognize when a situation may be escalating.",
    "The caregiver described the client's typical after-school routine, which helped tailor today's recommendations.",
    "The BCBA and caregiver discussed ways to acknowledge small wins at home to reinforce consistent use of the strategies by everyone involved.",
    "Today's session touched briefly on screen time and how it fits into the client's overall daily routine.",
    "The caregiver was encouraged to reach out to the BCBA directly if a new or unexpected behavior comes up at home.",
    "The BCBA reviewed how today's strategies connect to what the client is already working on during scheduled sessions.",
    "A brief conversation covered how other caregivers or babysitters might be introduced to a few of today's strategies.",
    "The caregiver mentioned a recent challenge during a car ride, which was used as a practical example during training.",
    "The BCBA and caregiver discussed pacing today's changes gradually rather than introducing everything at once.",
    "Today's session included a short discussion of how the client responds differently at home compared to school.",
    "The caregiver was given space to share what has been going well overall, not just areas that still need work.",
    "The BCBA suggested a simple way to signal an upcoming transition at home, similar to cues used during sessions.",
    "A brief check-in covered how the client has been eating lately, since nutrition can be a relevant factor in daily functioning.",
    "The caregiver and BCBA discussed how weekend routines differ from weekday routines and what that means for consistency.",
    "The BCBA offered a few troubleshooting tips in case a strategy stops producing the desired change after initially being effective.",
    "Today's training touched on how to keep instructions short and clear when the caregiver is busy with other tasks.",
]

ASSESSMENT_CONNECTORS = ["Additionally, ", "Furthermore, ", "Based on the assessment, ", "As part of the evaluation, ", ""]

INITIAL_ASSESSMENT_INTRO_TEMPLATES = [
    "This report documents the results of an initial assessment conducted for {name} at {place}. The assessment was completed by {bcba} in response to a {referral}.",
    "{bcba} conducted an initial assessment for {name} at {place} following a {referral}, in order to inform the development of an individualized treatment plan.",
    "This initial assessment report summarizes findings for {name}, evaluated by {bcba} at {place} following a {referral}.",
    "{name} was referred for an initial ABA assessment following a {referral}. The evaluation was conducted by {bcba} at {place}.",
]

ASSESSMENT_METHODS_TEMPLATES = [
    "The assessment included {methods}.",
    "The following assessment methods were used to gather information: {methods}.",
    "Information was gathered through {methods}.",
    "To inform this report, the BCBA utilized {methods}.",
]

INITIAL_BEHAVIORS_LEAD = [
    "Based on the assessment, concerns were identified in the following areas of behavior.",
    "The evaluation identified the following behaviors of concern.",
    "The following behaviors were identified as areas of concern during the assessment.",
]

INITIAL_SKILLS_LEAD_TEMPLATES = [
    "Skill acquisition needs were identified in the following areas based on the results of the assessment: {labels}.",
    "The assessment identified the following areas for skill acquisition programming: {labels}.",
    "Based on the evaluation, the following skill areas were identified as priorities for treatment: {labels}.",
    "The following areas were identified as priorities for skill acquisition programming: {labels}.",
]

INTENSITY_TEMPLATES = [
    "Based on the severity and breadth of identified needs, {intensity} is recommended.",
    "The BCBA recommends {intensity} based on the results of this assessment.",
    "Given the findings of this assessment, {intensity} is recommended to appropriately address identified needs.",
]

SERVICES_TEMPLATES = [
    "The following services are recommended as part of the treatment plan: {services}.",
    "Recommended services include {services}.",
    "To address identified needs, the following services are recommended: {services}.",
]

REASSESSMENT_INTRO_TEMPLATES = [
    "This report documents the results of a reassessment conducted for {name} at {place}, completed by {bcba} to review progress under the current treatment plan.",
    "{bcba} conducted a reassessment for {name} at {place} to evaluate progress and inform continued treatment planning.",
    "This reassessment report summarizes progress for {name}, evaluated by {bcba} at {place} since the prior assessment period.",
    "{name} was reassessed by {bcba} at {place} as part of ongoing treatment planning and progress monitoring.",
]

REASSESSMENT_PROGRESS_TEMPLATES = [
    "Overall, the client demonstrated {rating}.",
    "The client's progress reflected {rating}.",
    "The reassessment found {rating}.",
    "Review of the client's record and current data indicated {rating}.",
]

REASSESSMENT_GOALS_LEAD_TEMPLATES = [
    "Progress was reviewed across the following treatment goals: {labels}.",
    "The following skill acquisition goals were reviewed as part of this reassessment: {labels}.",
    "This reassessment reviewed the client's progress across the following goals: {labels}.",
]

REASSESSMENT_BEHAVIORS_LEAD = [
    "The following behaviors continue to be addressed under the current behavior intervention plan.",
    "The reassessment reviewed progress on the following behaviors of concern.",
    "The following behaviors of concern remain a focus of the current treatment plan.",
]

REASSESSMENT_DATA_TEMPLATES = [
    "{methods_cap} were used to monitor progress since the last assessment period.",
    "Progress was monitored using {methods} throughout the current treatment period.",
    "Data collected using {methods} were reviewed as part of this reassessment.",
]

REASSESSMENT_RECOMMENDATIONS_TEMPLATES = [
    "Based on this reassessment, the following recommendations are made: {recommendations}.",
    "The BCBA recommends the following changes to the treatment plan: {recommendations}.",
    "Moving forward, the following is recommended: {recommendations}.",
]

ASSESSMENT_FILLERS = [
    "Findings from this assessment will guide the development of the client's individualized treatment plan.",
    "This report reflects the client's presentation at the time of assessment and may be updated as new information comes in.",
    "The BCBA reviewed available developmental and treatment history as part of this assessment.",
    "Caregiver input shaped the assessment process throughout, so recommendations reflect the family's stated priorities.",
    "Current environment and daily routines were factored into the recommendations below.",
    "Recommendations in this report are meant to be reviewed and adjusted as treatment progresses, not treated as fixed.",
    "This assessment followed standard professional and ethical guidelines for behavior-analytic evaluation.",
    "What was gathered during this assessment will shape goal selection and prioritization going forward.",
    "Findings were considered against the client's broader developmental profile rather than in isolation.",
    "The BCBA will keep monitoring progress and adjust recommendations over time as needed.",
    "This report is meant for the treatment team and other stakeholders involved in the client's care.",
    "Both the client's strengths and identified areas of need factored into these recommendations.",
    "Assessment findings held up across multiple sources, including caregiver report and direct observation.",
    "These recommendations reflect current best practices in Applied Behavior Analysis.",
    "Where applicable, the client's response to previous intervention was factored into this evaluation.",
    "This report will go to the family and relevant care-team members once complete.",
    "Questions about the findings or recommendations in this report can be directed to the BCBA.",
    "Environmental factors relevant to the client's presentation were considered throughout.",
    "The client's current level of functioning across several domains factored into this assessment.",
    "Standardized and informal tools were used where appropriate to supplement observational data.",
    "These findings represent a point-in-time evaluation and may shift as more is learned.",
    "This report will serve as a reference point for tracking the client's progress going forward.",
    "Recommendations were checked against what's realistically feasible in the family's home and community setting.",
    "Staying in touch with the family will help keep recommendations aligned with the client's needs.",
    "The scope of this assessment followed from the original referral concern and available background information.",
    "Where applicable, results were reviewed together with other members of the client's care team.",
    "The BCBA plans to revisit these recommendations periodically as the client develops.",
    "This report draws on a comprehensive review of the information available at the time of evaluation.",
    "These findings will be added to the client's broader clinical record.",
    "The client's presentation during the assessment period was treated as representative of typical functioning.",
    "Additional information may be gathered in future sessions to sharpen treatment recommendations.",
    "Recommendations were prioritized with the client's safety, functioning, and quality of life in mind.",
    "Caregiver input on the client's behavior across multiple settings informed this evaluation.",
    "The BCBA will continue coordinating with other providers involved in the client's care as appropriate.",
    "These recommendations are meant to be individualized rather than generic, responsive to this client specifically.",
    "Available records were reviewed to flag any prior interventions or evaluations relevant to current planning.",
    "Where possible, observations spanned more than one setting to capture a fuller picture of the client's presentation.",
    "The assessment process also gave the BCBA a chance to build initial rapport with the client and family.",
    "Caregivers walked through daily routines in detail, which helped surface natural opportunities for intervention.",
    "Current communication abilities were noted as part of the overall picture from this evaluation.",
    "Sensory preferences and aversions the caregiver reported were noted for future programming.",
    "Available medical and developmental history was reviewed as part of this evaluation.",
    "What was gathered here will help determine how early treatment goals are sequenced.",
    "The BCBA walked the family through the assessment process to make sure next steps were clearly understood.",
    "Early observations of the client's play and social behavior were noted during this evaluation.",
    "The family's goals and priorities came up during the assessment and will factor into future planning.",
    "Where relevant information was available, this evaluation considered functioning relative to same-age peers.",
    "Findings here will help the BCBA decide which goals to prioritize in the earliest sessions.",
    "Scheduling and family availability, where known, were factored into these recommendations.",
    "This assessment is a snapshot of the client's current needs and is expected to evolve once treatment begins.",
    "Where possible, the BCBA asked for specific examples to better understand the function behind reported behaviors.",
    "The family had a chance to ask questions about the process and the proposed next steps.",
    "This report will be used alongside ongoing clinical judgment to guide the earliest phases of treatment.",
    "Cultural and family context factored into the recommendations included in this report.",
    "Overall, these findings point to the need for an approach tailored specifically to this client.",
    "A few data points stood out enough during the assessment to shape how early goals are sequenced.",
    "The BCBA weighed practical constraints alongside clinical priorities when drafting these recommendations.",
]


def load_options():
    with open(OPTIONS_PATH) as f:
        return json.load(f)


def word_count(text):
    return len(text.split())


def _by_id(items, ids):
    wanted = set(ids or [])
    return [i for i in items if i["id"] in wanted]


def _label_list(items, ids):
    chosen = _by_id(items, ids)
    return [i["label"] for i in chosen]


def _program_scenario(program, data=None):
    """Return the RBT-run scenario for this replacement program: a user-typed custom
    scenario (data["program_scenarios"][program_id] as a string) takes priority, then an
    explicit 0-based index choice, then a random pick from "blurbs"; falls back to a
    legacy single "blurb" string for programs that predate the "blurbs" list."""
    variants = program.get("blurbs")
    if not variants:
        return program.get("blurb", "")
    if data:
        raw_choice = (data.get("program_scenarios") or {}).get(program["id"])
        if isinstance(raw_choice, str) and raw_choice.strip():
            return raw_choice.strip()
        try:
            index = int(raw_choice)
            if 0 <= index < len(variants):
                return variants[index]
        except (TypeError, ValueError):
            pass
    return random.choice(variants)


def _behavior_topography(behavior, data=None):
    """Return the topography description for this maladaptive behavior: a user-typed
    custom description (data["behavior_topographies"][behavior_id] as a string) takes
    priority, then an explicit 0-based index choice, then the first "blurbs" variant
    by default (deterministic, not randomized); falls back to a legacy single "blurb"
    string for behaviors that predate the "blurbs" list."""
    variants = behavior.get("blurbs")
    if not variants:
        return behavior.get("blurb", "")
    if data:
        raw_choice = (data.get("behavior_topographies") or {}).get(behavior["id"])
        if isinstance(raw_choice, str) and raw_choice.strip():
            return raw_choice.strip()
        try:
            index = int(raw_choice)
            if 0 <= index < len(variants):
                return variants[index]
        except (TypeError, ValueError):
            pass
    return variants[0]


def _join_natural(items):
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def _condensed_labels(items, generic_phrase, threshold=6):
    """Avoid repeating a long label list twice in one note; use a short generic phrase instead."""
    if not items:
        return generic_phrase
    if len(items) > threshold:
        return generic_phrase
    return _join_natural(items)


def _duration_minutes(start_time, end_time):
    try:
        fmt = "%H:%M"
        start = datetime.strptime(start_time, fmt)
        end = datetime.strptime(end_time, fmt)
        delta = (end - start).total_seconds() / 60
        if delta < 0:
            delta += 24 * 60
        return int(delta)
    except Exception:
        return None


def _connector(is_first, pool=CONNECTORS):
    if is_first:
        return ""
    return random.choice(pool)


def _sentence(connector, text):
    """Join a connector phrase with sentence text, capitalizing only the true sentence start."""
    if connector:
        return f"{connector}{text}."
    return f"{text[0].upper()}{text[1:]}."


def _target_range(data):
    """User-selected target word count (with a +/-50 window), falling back to the 700-800 default."""
    try:
        target = int(data.get("target_word_count"))
    except (TypeError, ValueError):
        target = None
    if not target or target < 100:
        return TARGET_LOW, TARGET_HIGH
    return max(target - 50, 50), target + 50


def _pad_to_range(paragraphs, filler_pool, target_low=TARGET_LOW, target_high=TARGET_HIGH):
    text = "\n\n".join(p for p in paragraphs if p.strip())
    count = word_count(text)

    pool = list(filler_pool)
    random.shuffle(pool)

    extra_sentences = []
    for candidate in pool:
        if count >= target_low:
            break
        projected = count + word_count(candidate)
        if projected > target_high:
            continue
        extra_sentences.append(candidate)
        count = projected

    if extra_sentences:
        random.shuffle(extra_sentences)
        filler_paragraph = " ".join(extra_sentences)
        text = text + "\n\n" + filler_paragraph
        count = word_count(text)

    return text, count


def _session_context(data, options):
    """Shared lookups used by both the BCBA-observed and plain RBT session notes."""
    client = data["client"]
    programs = _by_id(options["replacement_programs"], data.get("replacement_programs"))
    behaviors = _by_id(options["maladaptive_behaviors"], data.get("maladaptive_behaviors"))
    data_methods = _label_list(options["data_collection_methods"], data.get("data_collection_methods"))
    engagement = next((e for e in options["client_engagement"] if e["id"] == data.get("client_engagement")), None)
    environmental_changes = _label_list(options["environmental_changes"], data.get("environmental_changes"))
    medical_concerns = _label_list(options["medical_concerns"], data.get("medical_concerns"))
    effectiveness = next(
        (e for e in options["intervention_effectiveness"] if e["id"] == data.get("intervention_effectiveness")), None
    )
    duration = _duration_minutes(data.get("start_time", ""), data.get("end_time", ""))
    duration_str = f"{duration}-minute " if duration else ""
    return (
        client, programs, behaviors, data_methods, engagement,
        environmental_changes, medical_concerns, effectiveness, duration_str,
    )


def _session_body_paragraphs(
    data, options, programs, behaviors, data_methods, engagement,
    environmental_changes=None, medical_concerns=None, effectiveness=None,
):
    """Programs/behaviors/data/summary paragraphs shared by both session note types."""
    context_parts = []
    if environmental_changes:
        context_parts.append(
            random.choice(ENVIRONMENTAL_CHANGE_TEMPLATES).format(changes=_join_natural(environmental_changes))
        )
    if medical_concerns:
        context_parts.append(
            random.choice(MEDICAL_CONCERN_TEMPLATES).format(concerns=_join_natural(medical_concerns))
        )
    context_para = " ".join(context_parts)

    programs_para = ""
    if programs:
        lead = random.choice(SESSION_PROGRAMS_LEAD)
        sentences = []
        for i, p in enumerate(programs):
            sentences.append(_sentence(_connector(i == 0), _program_scenario(p, data)))
        labels = _join_natural([p["label"] for p in programs])
        close = random.choice(SESSION_PROGRAMS_CLOSE).format(labels=labels)
        programs_para = " ".join([lead] + sentences + [close])

    behaviors_para = ""
    if behaviors:
        lead = random.choice(SESSION_BEHAVIOR_LEAD)
        sentences = []
        any_paired_intervention = False
        for i, b in enumerate(behaviors):
            topography = _behavior_topography(b, data)
            antecedent_ids = (data.get("behavior_antecedents") or {}).get(b["id"]) or []
            antecedent_labels = _label_list(options["antecedents"], antecedent_ids)
            paired_ids = (data.get("behavior_interventions") or {}).get(b["id"]) or []
            paired_labels = _label_list(options["intervention_strategies"], paired_ids)
            if paired_labels:
                any_paired_intervention = True

            if antecedent_labels and paired_labels:
                text = (
                    f"{topography} most often preceded by {_join_natural(antecedent_labels)}, "
                    f"was observed and addressed using {_join_natural(paired_labels)}"
                )
            elif antecedent_labels:
                text = f"{topography} most often preceded by {_join_natural(antecedent_labels)}, was observed and addressed"
            elif paired_labels:
                text = f"{topography} was observed and addressed using {_join_natural(paired_labels)}"
            else:
                text = f"{topography} was observed and addressed"
            sentences.append(_sentence(_connector(i == 0), text))
        parts = [lead] + sentences
        if any_paired_intervention and effectiveness:
            parts.append(random.choice(INTERVENTION_EFFECTIVENESS_TEMPLATES).format(blurb=effectiveness["blurb"]))
        behaviors_para = " ".join(parts)

    data_para = ""
    if data_methods:
        methods = _join_natural(data_methods)
        data_para = random.choice(SESSION_DATA_TEMPLATES).format(methods=methods, methods_cap=methods[0].upper() + methods[1:])

    engagement_sentence = engagement["blurb"] if engagement else ""
    extra_notes = data.get("additional_notes", "").strip()
    plan_text = data.get("plan_next_session", "").strip()
    if not plan_text:
        program_labels = _condensed_labels([p["label"] for p in programs], "the skill acquisition goals outlined above")
        plan_text = (
            f"programming will continue to target {program_labels} during the next scheduled session, "
            f"with continued behavioral support provided as needed."
        )
    else:
        plan_text = plan_text[0].lower() + plan_text[1:]

    if engagement_sentence:
        lead = random.choice(SESSION_SUMMARY_LEAD)
        summary_para = f"{lead}{engagement_sentence[0].lower() + engagement_sentence[1:]} Going forward, {plan_text}"
    else:
        summary_para = f"Going forward, {plan_text}"
    if extra_notes:
        summary_para += f" {extra_notes}"

    return context_para, programs_para, behaviors_para, data_para, summary_para


def _generate_reviewed_session_note(data, options, title, default_reviewer_label):
    """Shared by the BCBA and BCaBA session notes: a lead analyst observes and guides
    the RBT, with an optional protocol-modification narrative and direct-observation
    feedback section. Only the header title and the "no name given" fallback differ."""
    (
        client, programs, behaviors, data_methods, engagement,
        environmental_changes, medical_concerns, effectiveness, duration_str,
    ) = _session_context(data, options)

    header = _session_header(title, client, data)

    rbt_name = data.get("provider_name", "").strip() or "the RBT"
    rbt_credential = data.get("provider_credential", "").strip()
    rbt_display = f"{rbt_name} ({rbt_credential})" if rbt_credential else rbt_name
    reviewing_bcba_name = data.get("reviewing_bcba_name", "").strip()
    reviewing_bcba_credential = data.get("reviewing_bcba_credential", "").strip()
    bcba_display = (
        f"{reviewing_bcba_name} ({reviewing_bcba_credential})"
        if reviewing_bcba_name and reviewing_bcba_credential
        else reviewing_bcba_name or default_reviewer_label
    )
    reviewer_role = reviewing_bcba_credential or "BCBA"

    intro = random.choice(SESSION_INTRO_TEMPLATES).format(
        duration=duration_str,
        name=client["name"],
        place=data.get("place_of_service", "the scheduled location"),
        rbt=rbt_display,
        bcba=bcba_display,
    )
    intro = intro[0].upper() + intro[1:]
    if client.get("diagnosis"):
        intro += f" {client['name']} carries a diagnosis of {client['diagnosis']}."
    intro += _caregiver_presence_sentence(data)

    context_para, programs_para, behaviors_para, data_para, summary_para = _session_body_paragraphs(
        data, options, programs, behaviors, data_methods, engagement,
        environmental_changes, medical_concerns, effectiveness,
    )

    reviewing_bcba = data.get("reviewing_bcba_name", "").strip()
    observation_method = next((m for m in options["observation_methods"] if m["id"] == data.get("observation_method")), None)
    session_rating = next((r for r in options["session_ratings"] if r["id"] == data.get("session_rating")), None)
    fidelity = next((f for f in options["protocol_fidelity"] if f["id"] == data.get("protocol_fidelity")), None)
    rbt_strengths = _label_list(options["rbt_strengths"], data.get("rbt_strengths"))
    rbt_feedback_areas = _label_list(options["rbt_feedback_areas"], data.get("rbt_feedback_areas"))
    review_notes = data.get("review_additional_notes", "").strip()

    review_para = ""
    if reviewing_bcba and observation_method:
        parts = [
            random.choice(BCBA_REVIEW_LEAD).format(bcba_name=bcba_display, method=observation_method["label"].lower())
        ]
        if session_rating:
            parts.append(random.choice(BCBA_REVIEW_RATING_TEMPLATES).format(rating=session_rating["blurb"], reviewer=reviewer_role))
        if fidelity:
            parts.append(f"{fidelity['blurb'][0].upper() + fidelity['blurb'][1:]}.")
        if rbt_strengths:
            parts.append(random.choice(BCBA_REVIEW_STRENGTHS_TEMPLATES).format(strengths=_join_natural(rbt_strengths)))
        if rbt_feedback_areas:
            parts.append(random.choice(BCBA_REVIEW_FEEDBACK_TEMPLATES).format(feedback=_join_natural(rbt_feedback_areas), reviewer=reviewer_role))
        if review_notes:
            parts.append(review_notes)
        review_para = " ".join(parts)

    protocol_mod_para = _protocol_modification_paragraph(data, options, reviewer_role)

    paragraphs = [
        header,
        intro,
        context_para,
        programs_para,
        behaviors_para,
        data_para,
        protocol_mod_para,
        review_para,
        summary_para,
    ]

    text, count = _pad_to_range(paragraphs, SESSION_FILLERS, *_target_range(data))
    attestation = _documentation_attestation(data)
    if attestation:
        text = f"{text}\n\n{attestation}"
        count = word_count(text)
    return text, count


def generate_session_note(data, options):
    return _generate_reviewed_session_note(data, options, "BCBA SESSION NOTE", "the BCBA")


def generate_bcaba_session_note(data, options):
    return _generate_reviewed_session_note(data, options, "BCABA SESSION NOTE", "the BCaBA")


def generate_rbt_session_note(data, options):
    """Plain RBT-authored session note: no claim of BCBA presence, just what the RBT did."""
    (
        client, programs, behaviors, data_methods, engagement,
        environmental_changes, medical_concerns, effectiveness, duration_str,
    ) = _session_context(data, options)

    header = _session_header("RBT SESSION NOTE", client, data)

    rbt_name = data.get("provider_name", "").strip() or "the RBT"
    rbt_credential = data.get("provider_credential", "").strip()
    rbt_display = f"{rbt_name} ({rbt_credential})" if rbt_credential else rbt_name

    intro = random.choice(RBT_SESSION_INTRO_TEMPLATES).format(
        duration=duration_str,
        name=client["name"],
        place=data.get("place_of_service", "the scheduled location"),
        rbt=rbt_display,
    )
    intro = intro[0].upper() + intro[1:]
    if client.get("diagnosis"):
        intro += f" {client['name']} carries a diagnosis of {client['diagnosis']}."
    intro += _caregiver_presence_sentence(data)

    context_para, programs_para, behaviors_para, data_para, summary_para = _session_body_paragraphs(
        data, options, programs, behaviors, data_methods, engagement,
        environmental_changes, medical_concerns, effectiveness,
    )

    paragraphs = [
        header,
        intro,
        context_para,
        programs_para,
        behaviors_para,
        data_para,
        summary_para,
    ]

    text, count = _pad_to_range(paragraphs, SESSION_FILLERS, *_target_range(data))
    attestation = _documentation_attestation(data)
    if attestation:
        text = f"{text}\n\n{attestation}"
        count = word_count(text)
    return text, count


def generate_caregiver_note(data, options):
    client = data["client"]
    topics = _by_id(options["caregiver_training_topics"], data.get("training_topics"))
    methods = _label_list(options["teaching_methods"], data.get("teaching_methods"))
    competency = next((c for c in options["caregiver_competency"] if c["id"] == data.get("caregiver_competency")), None)
    responses = _by_id(options["caregiver_response"], data.get("caregiver_response"))
    barriers = _by_id(options["training_barriers"], data.get("training_barriers"))

    duration = _duration_minutes(data.get("start_time", ""), data.get("end_time", ""))
    duration_str = f"{duration}-minute " if duration else ""
    caregiver_name = data.get("caregiver_name", "").strip() or "the caregiver"

    header = (
        f"CAREGIVER TRAINING NOTE\n"
        f"Client: {client['name']}"
        + (f" (DOB: {client['dob']})" if client.get("dob") else "")
        + f"\nCaregiver: {data.get('caregiver_name', '')}"
        + (f" ({data.get('caregiver_relationship')})" if data.get("caregiver_relationship") else "")
        + f"\nPlace of Service: {data.get('place_of_service', '')}\n"
        f"Provider: {data.get('provider_name', '')}"
        + (f", {data.get('provider_credential')}" if data.get("provider_credential") else "")
    )

    intro = random.choice(CAREGIVER_INTRO_TEMPLATES).format(
        duration=duration_str,
        name=client["name"],
        caregiver=caregiver_name,
        place=data.get("place_of_service", "the scheduled location"),
        provider=data.get("provider_name", "the treating provider"),
    )

    topics_para = ""
    if topics:
        lead = random.choice(CAREGIVER_TOPICS_LEAD).format(name=client["name"])
        sentences = []
        for i, t in enumerate(topics):
            sentences.append(_sentence(_connector(i == 0), f"training addressed {t['blurb']}"))
        parts = [lead] + sentences
        if methods:
            joined = _join_natural(methods)
            parts.append(random.choice(CAREGIVER_METHOD_TEMPLATES).format(methods=joined, methods_cap=joined[0].upper() + joined[1:]))
        topics_para = " ".join(parts)

    competency_para = ""
    if competency:
        competency_para = f"{caregiver_name} {competency['blurb']}."

    response_para = ""
    if responses:
        sentences = [r["blurb"] for r in responses]
        response_para = f"During the session, {caregiver_name} " + _join_natural(sentences) + "."

    barriers_para = ""
    if barriers:
        sentences = [b["blurb"] for b in barriers]
        barriers_para = " ".join(f"{s[0].upper() + s[1:]}." for s in sentences)

    extra_notes = data.get("additional_notes", "").strip()
    plan_text = data.get("plan_next_session", "").strip()
    if not plan_text:
        topic_labels = _condensed_labels([t["label"] for t in topics], "the topics outlined above")
        plan_text = (
            f"the next caregiver training session will continue to reinforce {topic_labels}, with continued "
            f"opportunities for practice and feedback to support consistent implementation across settings."
        )
    else:
        plan_text = plan_text[0].lower() + plan_text[1:]

    summary_para = f"Going forward, {plan_text}"
    if extra_notes:
        summary_para += f" {extra_notes}"

    paragraphs = [
        header,
        intro,
        topics_para,
        competency_para,
        response_para,
        barriers_para,
        summary_para,
    ]

    text, count = _pad_to_range(paragraphs, CAREGIVER_FILLERS, *_target_range(data))
    return text, count


def _session_header(title, client, data):
    """Billing-relevant header block shared by the BCBA and RBT session notes:
    date of service and start/end time support CPT unit-based billing audits."""
    lines = [
        title,
        f"Client: {client['name']}" + (f" (DOB: {client['dob']})" if client.get("dob") else ""),
    ]
    if data.get("session_date"):
        lines.append(f"Date of Service: {data['session_date']}")
    if data.get("start_time") and data.get("end_time"):
        lines.append(f"Time: {data['start_time']} - {data['end_time']}")
    lines.append(f"Place of Service: {data.get('place_of_service', '')}")
    if data.get("cpt_code"):
        lines.append(f"CPT Code: {data['cpt_code']}")
    provider_name = data.get("provider_name", "").strip()
    provider_credential = data.get("provider_credential", "").strip()
    if provider_name:
        provider_line = f"Provider: {provider_name}" + (f", {provider_credential}" if provider_credential else "")
    else:
        provider_line = f"Provider: {f'the {provider_credential}' if provider_credential else 'not specified'}"
    lines.append(provider_line)
    return "\n".join(lines)


def _documentation_attestation(data):
    name = data.get("provider_name", "").strip()
    if not name:
        return ""
    credential = data.get("provider_credential", "").strip()
    who = f"{name}, {credential}" if credential else name
    date = data.get("session_date", "").strip()
    return f"Documentation completed electronically by {who} on {date}." if date else f"Documentation completed electronically by {who}."


def _protocol_modification_paragraph(data, options, reviewer_role="BCBA"):
    """CPT 97155 requires a narrative tying any real-time protocol change to the
    data/observation that prompted it and the client's response, distinct from
    general supervision feedback to the RBT."""
    mod_items = _by_id(options["protocol_modifications"], data.get("protocol_modifications"))
    if not mod_items:
        return ""
    changes = _join_natural([m.get("blurb") or m["label"] for m in mod_items])

    sentence = f"Based on real-time data and observation during the session, the {reviewer_role} modified the treatment protocol by {changes}."
    parts = [sentence]

    trigger = data.get("protocol_modification_data", "").strip()
    if trigger:
        clause = trigger[0].lower() + trigger[1:]
        parts.append(f"This modification was prompted by {clause}{'' if clause.endswith('.') else '.'}")

    response = data.get("protocol_modification_response", "").strip()
    if response:
        clause = response[0].lower() + response[1:]
        parts.append(f"Following the modification, {clause}{'' if clause.endswith('.') else '.'}")

    return " ".join(parts)


def _caregiver_presence_sentence(data):
    names = [n.strip() for n in (data.get("caregiver_participant_names") or []) if n.strip()]
    if not names:
        return ""
    joined = _join_natural(names)
    verb = "was" if len(names) == 1 else "were"
    return f" {joined} {verb} present for the session."


def _provider_display(data):
    name = data.get("provider_name", "").strip() or "the BCBA"
    credential = data.get("provider_credential", "").strip()
    return f"{name} ({credential})" if credential else name


def generate_initial_assessment(data, options):
    client = data["client"]
    referral = next((r for r in options["referral_reasons"] if r["id"] == data.get("referral_reason")), None)
    methods = _label_list(options["assessment_methods"], data.get("assessment_methods"))
    behaviors = _by_id(options["maladaptive_behaviors"], data.get("maladaptive_behaviors"))
    skill_programs = _by_id(options["replacement_programs"], data.get("replacement_programs"))
    intensity = next((i for i in options["treatment_intensity"] if i["id"] == data.get("treatment_intensity")), None)
    services = _label_list(options["recommended_services"], data.get("recommended_services"))

    bcba_display = _provider_display(data)

    header = (
        f"INITIAL ASSESSMENT REPORT\n"
        f"Client: {client['name']}"
        + (f" (DOB: {client['dob']})" if client.get("dob") else "")
        + f"\nPlace of Service: {data.get('place_of_service', '')}\n"
        f"CPT Code: 97151\n"
        f"Provider: {bcba_display}"
    )

    intro = random.choice(INITIAL_ASSESSMENT_INTRO_TEMPLATES).format(
        name=client["name"],
        place=data.get("place_of_service", "the scheduled location"),
        bcba=bcba_display,
        referral=(referral["label"].lower() if referral else "clinical referral"),
    )
    if client.get("diagnosis"):
        intro += f" {client['name']} carries a diagnosis of {client['diagnosis']}."

    methods_para = ""
    if methods:
        methods_para = random.choice(ASSESSMENT_METHODS_TEMPLATES).format(methods=_join_natural(methods))

    behaviors_para = ""
    if behaviors:
        lead = random.choice(INITIAL_BEHAVIORS_LEAD)
        sentences = []
        for i, b in enumerate(behaviors):
            sentences.append(_sentence(
                _connector(i == 0, ASSESSMENT_CONNECTORS),
                f"{_behavior_topography(b, data)} was identified as a primary area of concern based on caregiver report and direct observation"
            ))
        behaviors_para = " ".join([lead] + sentences)

    skills_para = ""
    if skill_programs:
        labels = _join_natural([p["label"] for p in skill_programs])
        skills_para = random.choice(INITIAL_SKILLS_LEAD_TEMPLATES).format(labels=labels)

    intensity_para = ""
    if intensity:
        intensity_para = random.choice(INTENSITY_TEMPLATES).format(intensity=intensity["blurb"])

    services_para = ""
    if services:
        services_para = random.choice(SERVICES_TEMPLATES).format(services=_join_natural(services))

    extra_notes = data.get("additional_notes", "").strip()
    plan_text = data.get("plan_next_session", "").strip()
    if not plan_text:
        plan_text = (
            "the BCBA will develop an individualized treatment plan addressing the skill acquisition and "
            "behavior reduction goals identified above, with services to begin as authorized."
        )
    else:
        plan_text = plan_text[0].lower() + plan_text[1:]

    summary_para = f"Going forward, {plan_text}"
    if extra_notes:
        summary_para += f" {extra_notes}"

    paragraphs = [
        header,
        intro,
        methods_para,
        behaviors_para,
        skills_para,
        intensity_para,
        services_para,
        summary_para,
    ]

    text, count = _pad_to_range(paragraphs, ASSESSMENT_FILLERS, *_target_range(data))
    return text, count


def generate_reassessment(data, options):
    client = data["client"]
    methods = _label_list(options["assessment_methods"], data.get("assessment_methods"))
    rating = next((r for r in options["progress_ratings"] if r["id"] == data.get("progress_rating")), None)
    behaviors = _by_id(options["maladaptive_behaviors"], data.get("maladaptive_behaviors"))
    goal_programs = _by_id(options["replacement_programs"], data.get("replacement_programs"))
    data_methods = _label_list(options["data_collection_methods"], data.get("data_collection_methods"))
    recommendations = _label_list(options["reassessment_recommendations"], data.get("reassessment_recommendations"))

    bcba_display = _provider_display(data)

    header = (
        f"REASSESSMENT REPORT\n"
        f"Client: {client['name']}"
        + (f" (DOB: {client['dob']})" if client.get("dob") else "")
        + f"\nPlace of Service: {data.get('place_of_service', '')}\n"
        f"CPT Code: 97151-TS\n"
        f"Provider: {bcba_display}"
    )

    intro = random.choice(REASSESSMENT_INTRO_TEMPLATES).format(
        name=client["name"],
        place=data.get("place_of_service", "the scheduled location"),
        bcba=bcba_display,
    )
    if client.get("diagnosis"):
        intro += f" {client['name']} carries a diagnosis of {client['diagnosis']}."

    progress_para = ""
    if rating:
        progress_para = random.choice(REASSESSMENT_PROGRESS_TEMPLATES).format(rating=rating["blurb"])

    goals_para = ""
    if goal_programs:
        labels = _join_natural([p["label"] for p in goal_programs])
        goals_para = random.choice(REASSESSMENT_GOALS_LEAD_TEMPLATES).format(labels=labels)

    behaviors_para = ""
    if behaviors:
        lead = random.choice(REASSESSMENT_BEHAVIORS_LEAD)
        sentences = []
        for i, b in enumerate(behaviors):
            sentences.append(_sentence(
                _connector(i == 0, ASSESSMENT_CONNECTORS),
                f"{_behavior_topography(b, data)} continues to be addressed under the current behavior intervention plan"
            ))
        behaviors_para = " ".join([lead] + sentences)

    data_para = ""
    if data_methods:
        methods_joined = _join_natural(data_methods)
        data_para = random.choice(REASSESSMENT_DATA_TEMPLATES).format(
            methods=methods_joined, methods_cap=methods_joined[0].upper() + methods_joined[1:]
        )

    recommendations_para = ""
    if recommendations:
        recommendations_para = random.choice(REASSESSMENT_RECOMMENDATIONS_TEMPLATES).format(
            recommendations=_join_natural(recommendations)
        )

    extra_notes = data.get("additional_notes", "").strip()
    plan_text = data.get("plan_next_session", "").strip()
    if not plan_text:
        plan_text = "treatment will continue with adjustments made based on the recommendations outlined above."
    else:
        plan_text = plan_text[0].lower() + plan_text[1:]

    summary_para = f"Going forward, {plan_text}"
    if extra_notes:
        summary_para += f" {extra_notes}"

    paragraphs = [
        header,
        intro,
        progress_para,
        goals_para,
        behaviors_para,
        data_para,
        recommendations_para,
        summary_para,
    ]

    text, count = _pad_to_range(paragraphs, ASSESSMENT_FILLERS, *_target_range(data))
    return text, count

/**
 * Qualtrics Block Identifier Scripts — Survey 2
 *
 * SETUP (do this once in Survey Flow):
 *   1. Add an Embedded Data element at the TOP of Survey Flow.
 *   2. Create these five fields (leave values blank — the JS will fill them):
 *        pre_block_id
 *        pre_topic
 *        pre_personalization
 *        pre_is_control
 *        topic_condition
 *
 * HOW TO USE:
 *   • Copy the matching snippet into the FIRST question of each block.
 *   • In Qualtrics, click the question → "Add JavaScript" → paste into
 *     the Qualtrics.SurveyEngine.addOnload(function(){ ... }) section.
 *   • The script fires as soon as the participant enters the block,
 *     before they answer anything.
 *
 * NAMING CONVENTION:
 *   pre_block_id  = "<CONDITION>_<TOPIC>"
 *                   e.g. PERS_TEAMS, NP_PLASTIC, CTRL_PE
 *   pre_topic     = "teams" | "plastic_ban" | "pe_mandatory"
 *   pre_personalization = "personalized" | "non_personalized" | "control"
 *   pre_is_control      = "0" (treatment) | "1" (control)
 */


// ============================================================
// BLOCK 1 — Teams · Personalized
// ============================================================
// Paste into the first question of the "Teams - Personalized" block.

Qualtrics.SurveyEngine.addOnload(function () {
    Qualtrics.SurveyEngine.setEmbeddedData('pre_block_id',       'PERS_TEAMS');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_topic',          'teams');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_personalization', 'personalized');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_is_control',     '0');
    Qualtrics.SurveyEngine.setEmbeddedData('topic_condition',    'teams');
});


// ============================================================
// BLOCK 2 — Teams · Non-Personalized
// ============================================================
// Paste into the first question of the "Teams - Non-Personalized" block.

Qualtrics.SurveyEngine.addOnload(function () {
    Qualtrics.SurveyEngine.setEmbeddedData('pre_block_id',       'NP_TEAMS');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_topic',          'teams');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_personalization', 'non_personalized');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_is_control',     '0');
    Qualtrics.SurveyEngine.setEmbeddedData('topic_condition',    'teams');
});


// ============================================================
// BLOCK 3 — Plastic Ban · Personalized
// ============================================================
// Paste into the first question of the "Plastic Ban - Personalized" block.

Qualtrics.SurveyEngine.addOnload(function () {
    Qualtrics.SurveyEngine.setEmbeddedData('pre_block_id',       'PERS_PLASTIC');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_topic',          'plastic_ban');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_personalization', 'personalized');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_is_control',     '0');
    Qualtrics.SurveyEngine.setEmbeddedData('topic_condition',    'plastic_ban');
});


// ============================================================
// BLOCK 4 — Plastic Ban · Non-Personalized
// ============================================================
// Paste into the first question of the "Plastic Ban - Non-Personalized" block.

Qualtrics.SurveyEngine.addOnload(function () {
    Qualtrics.SurveyEngine.setEmbeddedData('pre_block_id',       'NP_PLASTIC');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_topic',          'plastic_ban');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_personalization', 'non_personalized');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_is_control',     '0');
    Qualtrics.SurveyEngine.setEmbeddedData('topic_condition',    'plastic_ban');
});


// ============================================================
// BLOCK 5 — PE Mandatory · Personalized
// ============================================================
// Paste into the first question of the "PE Mandatory - Personalized" block.

Qualtrics.SurveyEngine.addOnload(function () {
    Qualtrics.SurveyEngine.setEmbeddedData('pre_block_id',       'PERS_PE');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_topic',          'pe_mandatory');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_personalization', 'personalized');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_is_control',     '0');
    Qualtrics.SurveyEngine.setEmbeddedData('topic_condition',    'pe_mandatory');
});


// ============================================================
// BLOCK 6 — PE Mandatory · Non-Personalized
// ============================================================
// Paste into the first question of the "PE Mandatory - Non-Personalized" block.

Qualtrics.SurveyEngine.addOnload(function () {
    Qualtrics.SurveyEngine.setEmbeddedData('pre_block_id',       'NP_PE');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_topic',          'pe_mandatory');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_personalization', 'non_personalized');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_is_control',     '0');
    Qualtrics.SurveyEngine.setEmbeddedData('topic_condition',    'pe_mandatory');
});


// ============================================================
// BLOCK 7a — Control · Teams
// ============================================================
// The 7th top-level block is itself a randomizer with 3 sub-blocks.
// Paste this into the first question of the "Control - Teams" sub-block.

Qualtrics.SurveyEngine.addOnload(function () {
    Qualtrics.SurveyEngine.setEmbeddedData('pre_block_id',       'CTRL_TEAMS');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_topic',          'teams');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_personalization', 'control');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_is_control',     '1');
    Qualtrics.SurveyEngine.setEmbeddedData('topic_condition',    'teams');
});


// ============================================================
// BLOCK 7b — Control · Plastic Ban
// ============================================================
// Paste into the first question of the "Control - Plastic Ban" sub-block.

Qualtrics.SurveyEngine.addOnload(function () {
    Qualtrics.SurveyEngine.setEmbeddedData('pre_block_id',       'CTRL_PLASTIC');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_topic',          'plastic_ban');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_personalization', 'control');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_is_control',     '1');
    Qualtrics.SurveyEngine.setEmbeddedData('topic_condition',    'plastic_ban');
});


// ============================================================
// BLOCK 7c — Control · PE Mandatory
// ============================================================
// Paste into the first question of the "Control - PE Mandatory" sub-block.

Qualtrics.SurveyEngine.addOnload(function () {
    Qualtrics.SurveyEngine.setEmbeddedData('pre_block_id',       'CTRL_PE');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_topic',          'pe_mandatory');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_personalization', 'control');
    Qualtrics.SurveyEngine.setEmbeddedData('pre_is_control',     '1');
    Qualtrics.SurveyEngine.setEmbeddedData('topic_condition',    'pe_mandatory');
});

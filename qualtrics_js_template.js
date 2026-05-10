/**
 * Qualtrics JavaScript Template for Survey 1 API Integration
 *
 * This survey uses ChoiceGroup/SelectedChoices for many questions.
 * Matrix tables: use ${q://QIDx/ChoiceGroup/SelectedChoices/N} for row N (1-7).
 * Single Likert / MC: use ${q://QIDx/ChoiceGroup/SelectedChoices} (no row index).
 * Text entry: ChoiceTextEntryValue
 *
 * INSTRUCTIONS:
 * 1. Set API_URL to your deployed backend.
 * 2. Attach this JS to a question AFTER all answers exist (e.g. after QID42 for comment).
 * 3. If any QID in allBlocks does not match your survey, update the map below.
 */

Qualtrics.SurveyEngine.addOnReady(function() {
    var API_URL = 'https://chatbot-survey-temp-984481216259.us-central1.run.app/api/v1/survey1';
    console.log('[survey1] JS started');

    // ----- Helpers -----

    function pipedInt(val) {
        if (!val || val.indexOf('$' + '{') === 0) return null;
        var n = parseInt(val, 10);
        return isNaN(n) ? null : n;
    }

    /** ChoiceGroup/SelectedChoices often returns labels like "4. Rather agree (4)" — extract 1-6 */
    function pipedLikert(val) {
        if (!val || val.indexOf('$' + '{') === 0) return null;
        val = String(val).trim();
        var m = val.match(/\((\d+)\)\s*$/);
        if (m && m[1]) return pipedInt(m[1]);
        m = val.match(/\b(\d+)\b/);
        if (m && m[1]) return pipedInt(m[1]);
        var norm = val.toLowerCase().replace(/\s+/g, ' ').trim();
        var labelToNum = {
            "completely disagree": 1,
            "disagree": 2,
            "rather disagree": 3,
            "rather agree": 4,
            "agree": 5,
            "completely agree": 6,
            "not at all": 1,
            "very strongly": 6,
            "very important": 6
        };
        if (Object.prototype.hasOwnProperty.call(labelToNum, norm)) return labelToNum[norm];
        return null;
    }

    function pipedStr(val) {
        if (!val || val.indexOf('$' + '{') === 0) return null;
        return val;
    }

    /** Qualtrics substitutes $ piped text before this script runs. Use two candidate paths when unsure (matrix /1 vs single Likert). */
    function pipedLikertEither(a, b) {
        return pipedLikert(a) || pipedLikert(b);
    }
    function pipedStrEither(a, b) {
        return pipedStr(a) || pipedStr(b);
    }

    /** Try multiple piped strings (Qualtrics substitutes before this script runs). */
    function pipedStrFirst() {
        for (var i = 0; i < arguments.length; i++) {
            var s = pipedStr(arguments[i]);
            if (s !== null) return s;
        }
        return null;
    }

    /** Likert from choice labels, then SelectedAnswerRecode/1 (numeric) when labels are empty. */
    function pipedLikertOrRecode(choiceRow1, choiceNoRow, recodeRow1) {
        return pipedLikertEither(choiceRow1, choiceNoRow) || pipedInt(recodeRow1);
    }

    /** Matrix row: choice label, then recode (numeric), then raw int on choice (some surveys export choice id only). */
    function pipedMatrixRow(choiceStr, recodeStr) {
        var v = pipedLikert(choiceStr);
        if (v !== null) return v;
        v = pipedLikert(recodeStr);
        if (v !== null) return v;
        v = pipedInt(recodeStr);
        if (v !== null) return v;
        return pipedInt(pipedStr(choiceStr));
    }

    /**
     * Qualtrics sometimes pipes the same string for every matrix row: all row labels concatenated
     * (often comma-separated). Split into exactly 7 parts for stmt1..stmt7 when possible.
     */
    function trySplitSevenCommaSeparatedStatements(s) {
        if (!s || typeof s !== 'string') return null;
        var t = s.trim();
        if (!t) return null;
        var parts = t.split(', ');
        if (parts.length === 7) {
            for (var p = 0; p < 7; p++) {
                parts[p] = parts[p].trim();
            }
            return parts;
        }
        parts = t.split(',');
        if (parts.length === 7) {
            for (var q = 0; q < 7; q++) {
                parts[q] = parts[q].trim();
            }
            return parts;
        }
        return null;
    }

    /** 6-point agree–disagree scale used by statement matrix and opinion items (same numeric coding as pipedLikert). */
    var LIKERT_AGREE_1_6 = {
        1: 'Completely disagree',
        2: 'Disagree',
        3: 'Rather disagree',
        4: 'Rather agree',
        5: 'Agree',
        6: 'Completely agree'
    };
    function likertAgreeLabel(n) {
        if (n === null || n === undefined) return null;
        return Object.prototype.hasOwnProperty.call(LIKERT_AGREE_1_6, n) ? LIKERT_AGREE_1_6[n] : null;
    }

    /** Qualtrics bipolar exports endpoints in one string: Left||QBipolarDelim||Right. The click position is usually SelectedAnswerRecode/1 (1–6). */
    var POLITICAL_BIPOLAR_DELIM = '||QBipolarDelim||';
    function parsePoliticalBipolar(raw) {
        if (!raw || typeof raw !== 'string') return null;
        var t = raw.trim();
        if (t.indexOf(POLITICAL_BIPOLAR_DELIM) === -1) {
            return { selection_text: t, left_label: null, right_label: null, display: null };
        }
        var parts = t.split(POLITICAL_BIPOLAR_DELIM);
        if (parts.length !== 2) {
            return { selection_text: t, left_label: null, right_label: null, display: null };
        }
        var L = parts[0].trim();
        var R = parts[1].trim();
        return {
            selection_text: null,
            left_label: L,
            right_label: R,
            display: L + ' — ' + R
        };
    }

    // ----- Participant identification -----

    var participantId  = "${e://Field/ResponseID}";
    var prolificId     = pipedStr("${url:PROLIFIC_PID}")
                      || pipedStr("${e://Field/prolific_id}")
                      || null;
    var qualtricsResponseId = "${e://Field/ResponseID}";
    console.log('[survey1] IDs', { participantId: participantId, qualtricsResponseId: qualtricsResponseId, prolificId: prolificId });

    // ----- Block metadata (set by block identifier JS) -----

    var preBlockId        = pipedStr("${e://Field/pre_block_id}");
    var preTopic          = pipedStr("${e://Field/pre_topic}");
    var prePersonalization = pipedStr("${e://Field/pre_personalization}");
    var preIsControlRaw   = pipedStr("${e://Field/pre_is_control}");
    var topicCondition    = pipedStr("${e://Field/topic_condition}");

    var preIsControl = null;
    if (preIsControlRaw !== null) {
        preIsControl = (preIsControlRaw === '1' || preIsControlRaw === 'true');
    }
    console.log('[survey1] Embedded data', { preBlockId: preBlockId, preTopic: preTopic, prePersonalization: prePersonalization, preIsControl: preIsControl, topicCondition: topicCondition });

    // ----- Demographics & topic (ChoiceGroup/SelectedChoices per your survey) -----

    var age             = pipedInt("${q://QID18/ChoiceTextEntryValue}");
    var gender          = pipedStr("${q://QID19/ChoiceGroup/SelectedChoices}");
    var education       = pipedStr("${q://QID20/ChoiceGroup/SelectedChoices}");
    var politicalBelief = pipedStr("${q://QID21/ChoiceGroup/SelectedChoices}");
    /** Bipolar slider / scale: 1 = toward left label, 6 = toward right label (verify in your survey’s recode). */
    var politicalBeliefRecode = pipedInt("${q://QID21/SelectedAnswerRecode/1}");
    var kidsInSchool    = pipedStr("${q://QID22/ChoiceGroup/SelectedChoices}");

    var demographics = {};
    if (age !== null)             demographics.age = age;
    if (gender !== null)          demographics.gender = gender;
    if (education !== null)       demographics.education = education;
    if (kidsInSchool !== null)    demographics.kids_in_school = kidsInSchool;
    if (politicalBelief !== null) demographics.political_belief = politicalBelief;
    if (politicalBeliefRecode !== null) demographics.political_belief_scale_position = politicalBeliefRecode;
    var pbParsed = parsePoliticalBipolar(politicalBelief);
    if (pbParsed) {
        if (pbParsed.left_label !== null)  demographics.political_belief_left_label = pbParsed.left_label;
        if (pbParsed.right_label !== null) demographics.political_belief_right_label = pbParsed.right_label;
        if (pbParsed.display)              demographics.political_belief_display = pbParsed.display;
    }

    var topicUsage    = pipedStr("${q://QID23/ChoiceGroup/SelectedChoices}");
    var topicBehavior = pipedStr("${q://QID24/ChoiceGroup/SelectedChoices}");
    console.log('[survey1] Demographics & topic qs', { demographics: demographics, topicUsage: topicUsage, topicBehavior: topicBehavior });

    var surveyComment = pipedStr("${q://QID42/ChoiceTextEntryValue}");

    // ----- Block responses -----
    // Statements matrix: ChoiceGroup/SelectedChoices/1–/7 (SelectedAnswerRecode is often empty in piped text).
    // Statement row labels: try AnswerGroup/ChoiceDescription before ChoiceGroup (ChoiceGroup often describes scale columns).
    // If every row shows the same comma-separated blob, trySplitSevenCommaSeparatedStatements maps stmt1..stmt7.
    // Opinion / importance: pipedLikertOrRecode adds SelectedAnswerRecode/1 when labels are empty.
    // Reason: pipedStrFirst(ChoiceTextEntryValue, /1, /2) for multi-field forms.

    var allBlocks = {

        'NP_TEAMS': {
            opinion: pipedLikertOrRecode("${q://QID11/ChoiceGroup/SelectedChoices/1}", "${q://QID11/ChoiceGroup/SelectedChoices}", "${q://QID11/SelectedAnswerRecode/1}"),
            reason: pipedStrFirst("${q://QID2/ChoiceTextEntryValue}", "${q://QID2/ChoiceTextEntryValue/1}", "${q://QID2/ChoiceTextEntryValue/2}"),
            stmts: [
                pipedMatrixRow("${q://QID3/ChoiceGroup/SelectedChoices/1}", "${q://QID3/SelectedAnswerRecode/1}"),
                pipedMatrixRow("${q://QID3/ChoiceGroup/SelectedChoices/2}", "${q://QID3/SelectedAnswerRecode/2}"),
                pipedMatrixRow("${q://QID3/ChoiceGroup/SelectedChoices/3}", "${q://QID3/SelectedAnswerRecode/3}"),
                pipedMatrixRow("${q://QID3/ChoiceGroup/SelectedChoices/4}", "${q://QID3/SelectedAnswerRecode/4}"),
                pipedMatrixRow("${q://QID3/ChoiceGroup/SelectedChoices/5}", "${q://QID3/SelectedAnswerRecode/5}"),
                pipedMatrixRow("${q://QID3/ChoiceGroup/SelectedChoices/6}", "${q://QID3/SelectedAnswerRecode/6}"),
                pipedMatrixRow("${q://QID3/ChoiceGroup/SelectedChoices/7}", "${q://QID3/SelectedAnswerRecode/7}")
            ],
            stmt_texts: [
                pipedStrFirst("${q://QID3/AnswerGroup/ChoiceDescription/1}", "${q://QID3/AnswerGroup/DisplayedChoices/1}", "${q://QID3/ChoiceGroup/ChoiceDescription/1}", "${q://QID3/ChoiceGroup/DisplayedChoices/1}"),
                pipedStrFirst("${q://QID3/AnswerGroup/ChoiceDescription/2}", "${q://QID3/AnswerGroup/DisplayedChoices/2}", "${q://QID3/ChoiceGroup/ChoiceDescription/2}", "${q://QID3/ChoiceGroup/DisplayedChoices/2}"),
                pipedStrFirst("${q://QID3/AnswerGroup/ChoiceDescription/3}", "${q://QID3/AnswerGroup/DisplayedChoices/3}", "${q://QID3/ChoiceGroup/ChoiceDescription/3}", "${q://QID3/ChoiceGroup/DisplayedChoices/3}"),
                pipedStrFirst("${q://QID3/AnswerGroup/ChoiceDescription/4}", "${q://QID3/AnswerGroup/DisplayedChoices/4}", "${q://QID3/ChoiceGroup/ChoiceDescription/4}", "${q://QID3/ChoiceGroup/DisplayedChoices/4}"),
                pipedStrFirst("${q://QID3/AnswerGroup/ChoiceDescription/5}", "${q://QID3/AnswerGroup/DisplayedChoices/5}", "${q://QID3/ChoiceGroup/ChoiceDescription/5}", "${q://QID3/ChoiceGroup/DisplayedChoices/5}"),
                pipedStrFirst("${q://QID3/AnswerGroup/ChoiceDescription/6}", "${q://QID3/AnswerGroup/DisplayedChoices/6}", "${q://QID3/ChoiceGroup/ChoiceDescription/6}", "${q://QID3/ChoiceGroup/DisplayedChoices/6}"),
                pipedStrFirst("${q://QID3/AnswerGroup/ChoiceDescription/7}", "${q://QID3/AnswerGroup/DisplayedChoices/7}", "${q://QID3/ChoiceGroup/ChoiceDescription/7}", "${q://QID3/ChoiceGroup/DisplayedChoices/7}")
            ],
            feeling:    pipedLikert("${q://QID70/ChoiceGroup/SelectedChoices}"),
            importance: pipedLikertOrRecode("${q://QID5/ChoiceGroup/SelectedChoices}", "${q://QID5/ChoiceGroup/SelectedChoices/1}", "${q://QID5/SelectedAnswerRecode/1}")
        },

        'PERS_TEAMS': {
            opinion: pipedLikertOrRecode("${q://QID72/ChoiceGroup/SelectedChoices/1}", "${q://QID72/ChoiceGroup/SelectedChoices}", "${q://QID72/SelectedAnswerRecode/1}"),
            reason: pipedStrFirst("${q://QID73/ChoiceTextEntryValue}", "${q://QID73/ChoiceTextEntryValue/1}", "${q://QID73/ChoiceTextEntryValue/2}"),
            stmts: [
                pipedMatrixRow("${q://QID74/ChoiceGroup/SelectedChoices/1}", "${q://QID74/SelectedAnswerRecode/1}"),
                pipedMatrixRow("${q://QID74/ChoiceGroup/SelectedChoices/2}", "${q://QID74/SelectedAnswerRecode/2}"),
                pipedMatrixRow("${q://QID74/ChoiceGroup/SelectedChoices/3}", "${q://QID74/SelectedAnswerRecode/3}"),
                pipedMatrixRow("${q://QID74/ChoiceGroup/SelectedChoices/4}", "${q://QID74/SelectedAnswerRecode/4}"),
                pipedMatrixRow("${q://QID74/ChoiceGroup/SelectedChoices/5}", "${q://QID74/SelectedAnswerRecode/5}"),
                pipedMatrixRow("${q://QID74/ChoiceGroup/SelectedChoices/6}", "${q://QID74/SelectedAnswerRecode/6}"),
                pipedMatrixRow("${q://QID74/ChoiceGroup/SelectedChoices/7}", "${q://QID74/SelectedAnswerRecode/7}")
            ],
            stmt_texts: [
                pipedStrFirst("${q://QID74/AnswerGroup/ChoiceDescription/1}", "${q://QID74/AnswerGroup/DisplayedChoices/1}", "${q://QID74/ChoiceGroup/ChoiceDescription/1}", "${q://QID74/ChoiceGroup/DisplayedChoices/1}"),
                pipedStrFirst("${q://QID74/AnswerGroup/ChoiceDescription/2}", "${q://QID74/AnswerGroup/DisplayedChoices/2}", "${q://QID74/ChoiceGroup/ChoiceDescription/2}", "${q://QID74/ChoiceGroup/DisplayedChoices/2}"),
                pipedStrFirst("${q://QID74/AnswerGroup/ChoiceDescription/3}", "${q://QID74/AnswerGroup/DisplayedChoices/3}", "${q://QID74/ChoiceGroup/ChoiceDescription/3}", "${q://QID74/ChoiceGroup/DisplayedChoices/3}"),
                pipedStrFirst("${q://QID74/AnswerGroup/ChoiceDescription/4}", "${q://QID74/AnswerGroup/DisplayedChoices/4}", "${q://QID74/ChoiceGroup/ChoiceDescription/4}", "${q://QID74/ChoiceGroup/DisplayedChoices/4}"),
                pipedStrFirst("${q://QID74/AnswerGroup/ChoiceDescription/5}", "${q://QID74/AnswerGroup/DisplayedChoices/5}", "${q://QID74/ChoiceGroup/ChoiceDescription/5}", "${q://QID74/ChoiceGroup/DisplayedChoices/5}"),
                pipedStrFirst("${q://QID74/AnswerGroup/ChoiceDescription/6}", "${q://QID74/AnswerGroup/DisplayedChoices/6}", "${q://QID74/ChoiceGroup/ChoiceDescription/6}", "${q://QID74/ChoiceGroup/DisplayedChoices/6}"),
                pipedStrFirst("${q://QID74/AnswerGroup/ChoiceDescription/7}", "${q://QID74/AnswerGroup/DisplayedChoices/7}", "${q://QID74/ChoiceGroup/ChoiceDescription/7}", "${q://QID74/ChoiceGroup/DisplayedChoices/7}")
            ],
            feeling:    pipedLikert("${q://QID75/ChoiceGroup/SelectedChoices}"),
            importance: pipedLikertOrRecode("${q://QID76/ChoiceGroup/SelectedChoices}", "${q://QID76/ChoiceGroup/SelectedChoices/1}", "${q://QID76/SelectedAnswerRecode/1}")
        },

        'NP_PLASTIC': {
            opinion: pipedLikertOrRecode("${q://QID12/ChoiceGroup/SelectedChoices/1}", "${q://QID12/ChoiceGroup/SelectedChoices}", "${q://QID12/SelectedAnswerRecode/1}"),
            reason: pipedStrFirst("${q://QID7/ChoiceTextEntryValue}", "${q://QID7/ChoiceTextEntryValue/1}", "${q://QID7/ChoiceTextEntryValue/2}"),
            stmts: [
                pipedMatrixRow("${q://QID8/ChoiceGroup/SelectedChoices/1}", "${q://QID8/SelectedAnswerRecode/1}"),
                pipedMatrixRow("${q://QID8/ChoiceGroup/SelectedChoices/2}", "${q://QID8/SelectedAnswerRecode/2}"),
                pipedMatrixRow("${q://QID8/ChoiceGroup/SelectedChoices/3}", "${q://QID8/SelectedAnswerRecode/3}"),
                pipedMatrixRow("${q://QID8/ChoiceGroup/SelectedChoices/4}", "${q://QID8/SelectedAnswerRecode/4}"),
                pipedMatrixRow("${q://QID8/ChoiceGroup/SelectedChoices/5}", "${q://QID8/SelectedAnswerRecode/5}"),
                pipedMatrixRow("${q://QID8/ChoiceGroup/SelectedChoices/6}", "${q://QID8/SelectedAnswerRecode/6}"),
                pipedMatrixRow("${q://QID8/ChoiceGroup/SelectedChoices/7}", "${q://QID8/SelectedAnswerRecode/7}")
            ],
            stmt_texts: [
                pipedStrFirst("${q://QID8/AnswerGroup/ChoiceDescription/1}", "${q://QID8/AnswerGroup/DisplayedChoices/1}", "${q://QID8/ChoiceGroup/ChoiceDescription/1}", "${q://QID8/ChoiceGroup/DisplayedChoices/1}"),
                pipedStrFirst("${q://QID8/AnswerGroup/ChoiceDescription/2}", "${q://QID8/AnswerGroup/DisplayedChoices/2}", "${q://QID8/ChoiceGroup/ChoiceDescription/2}", "${q://QID8/ChoiceGroup/DisplayedChoices/2}"),
                pipedStrFirst("${q://QID8/AnswerGroup/ChoiceDescription/3}", "${q://QID8/AnswerGroup/DisplayedChoices/3}", "${q://QID8/ChoiceGroup/ChoiceDescription/3}", "${q://QID8/ChoiceGroup/DisplayedChoices/3}"),
                pipedStrFirst("${q://QID8/AnswerGroup/ChoiceDescription/4}", "${q://QID8/AnswerGroup/DisplayedChoices/4}", "${q://QID8/ChoiceGroup/ChoiceDescription/4}", "${q://QID8/ChoiceGroup/DisplayedChoices/4}"),
                pipedStrFirst("${q://QID8/AnswerGroup/ChoiceDescription/5}", "${q://QID8/AnswerGroup/DisplayedChoices/5}", "${q://QID8/ChoiceGroup/ChoiceDescription/5}", "${q://QID8/ChoiceGroup/DisplayedChoices/5}"),
                pipedStrFirst("${q://QID8/AnswerGroup/ChoiceDescription/6}", "${q://QID8/AnswerGroup/DisplayedChoices/6}", "${q://QID8/ChoiceGroup/ChoiceDescription/6}", "${q://QID8/ChoiceGroup/DisplayedChoices/6}"),
                pipedStrFirst("${q://QID8/AnswerGroup/ChoiceDescription/7}", "${q://QID8/AnswerGroup/DisplayedChoices/7}", "${q://QID8/ChoiceGroup/ChoiceDescription/7}", "${q://QID8/ChoiceGroup/DisplayedChoices/7}")
            ],
            feeling:    pipedLikert("${q://QID9/ChoiceGroup/SelectedChoices}"),
            importance: pipedLikertOrRecode("${q://QID10/ChoiceGroup/SelectedChoices}", "${q://QID10/ChoiceGroup/SelectedChoices/1}", "${q://QID10/SelectedAnswerRecode/1}")
        },

        'PERS_PLASTIC': {
            opinion: pipedLikertOrRecode("${q://QID77/ChoiceGroup/SelectedChoices/1}", "${q://QID77/ChoiceGroup/SelectedChoices}", "${q://QID77/SelectedAnswerRecode/1}"),
            reason: pipedStrFirst("${q://QID78/ChoiceTextEntryValue}", "${q://QID78/ChoiceTextEntryValue/1}", "${q://QID78/ChoiceTextEntryValue/2}"),
            stmts: [
                pipedMatrixRow("${q://QID79/ChoiceGroup/SelectedChoices/1}", "${q://QID79/SelectedAnswerRecode/1}"),
                pipedMatrixRow("${q://QID79/ChoiceGroup/SelectedChoices/2}", "${q://QID79/SelectedAnswerRecode/2}"),
                pipedMatrixRow("${q://QID79/ChoiceGroup/SelectedChoices/3}", "${q://QID79/SelectedAnswerRecode/3}"),
                pipedMatrixRow("${q://QID79/ChoiceGroup/SelectedChoices/4}", "${q://QID79/SelectedAnswerRecode/4}"),
                pipedMatrixRow("${q://QID79/ChoiceGroup/SelectedChoices/5}", "${q://QID79/SelectedAnswerRecode/5}"),
                pipedMatrixRow("${q://QID79/ChoiceGroup/SelectedChoices/6}", "${q://QID79/SelectedAnswerRecode/6}"),
                pipedMatrixRow("${q://QID79/ChoiceGroup/SelectedChoices/7}", "${q://QID79/SelectedAnswerRecode/7}")
            ],
            stmt_texts: [
                pipedStrFirst("${q://QID79/AnswerGroup/ChoiceDescription/1}", "${q://QID79/AnswerGroup/DisplayedChoices/1}", "${q://QID79/ChoiceGroup/ChoiceDescription/1}", "${q://QID79/ChoiceGroup/DisplayedChoices/1}"),
                pipedStrFirst("${q://QID79/AnswerGroup/ChoiceDescription/2}", "${q://QID79/AnswerGroup/DisplayedChoices/2}", "${q://QID79/ChoiceGroup/ChoiceDescription/2}", "${q://QID79/ChoiceGroup/DisplayedChoices/2}"),
                pipedStrFirst("${q://QID79/AnswerGroup/ChoiceDescription/3}", "${q://QID79/AnswerGroup/DisplayedChoices/3}", "${q://QID79/ChoiceGroup/ChoiceDescription/3}", "${q://QID79/ChoiceGroup/DisplayedChoices/3}"),
                pipedStrFirst("${q://QID79/AnswerGroup/ChoiceDescription/4}", "${q://QID79/AnswerGroup/DisplayedChoices/4}", "${q://QID79/ChoiceGroup/ChoiceDescription/4}", "${q://QID79/ChoiceGroup/DisplayedChoices/4}"),
                pipedStrFirst("${q://QID79/AnswerGroup/ChoiceDescription/5}", "${q://QID79/AnswerGroup/DisplayedChoices/5}", "${q://QID79/ChoiceGroup/ChoiceDescription/5}", "${q://QID79/ChoiceGroup/DisplayedChoices/5}"),
                pipedStrFirst("${q://QID79/AnswerGroup/ChoiceDescription/6}", "${q://QID79/AnswerGroup/DisplayedChoices/6}", "${q://QID79/ChoiceGroup/ChoiceDescription/6}", "${q://QID79/ChoiceGroup/DisplayedChoices/6}"),
                pipedStrFirst("${q://QID79/AnswerGroup/ChoiceDescription/7}", "${q://QID79/AnswerGroup/DisplayedChoices/7}", "${q://QID79/ChoiceGroup/ChoiceDescription/7}", "${q://QID79/ChoiceGroup/DisplayedChoices/7}")
            ],
            feeling:    pipedLikert("${q://QID80/ChoiceGroup/SelectedChoices}"),
            importance: pipedLikertOrRecode("${q://QID81/ChoiceGroup/SelectedChoices}", "${q://QID81/ChoiceGroup/SelectedChoices/1}", "${q://QID81/SelectedAnswerRecode/1}")
        },

        'NP_PE': {
            opinion: pipedLikertOrRecode("${q://QID13/ChoiceGroup/SelectedChoices/1}", "${q://QID13/ChoiceGroup/SelectedChoices}", "${q://QID13/SelectedAnswerRecode/1}"),
            reason: pipedStrFirst("${q://QID14/ChoiceTextEntryValue}", "${q://QID14/ChoiceTextEntryValue/1}", "${q://QID14/ChoiceTextEntryValue/2}"),
            stmts: [
                pipedMatrixRow("${q://QID15/ChoiceGroup/SelectedChoices/1}", "${q://QID15/SelectedAnswerRecode/1}"),
                pipedMatrixRow("${q://QID15/ChoiceGroup/SelectedChoices/2}", "${q://QID15/SelectedAnswerRecode/2}"),
                pipedMatrixRow("${q://QID15/ChoiceGroup/SelectedChoices/3}", "${q://QID15/SelectedAnswerRecode/3}"),
                pipedMatrixRow("${q://QID15/ChoiceGroup/SelectedChoices/4}", "${q://QID15/SelectedAnswerRecode/4}"),
                pipedMatrixRow("${q://QID15/ChoiceGroup/SelectedChoices/5}", "${q://QID15/SelectedAnswerRecode/5}"),
                pipedMatrixRow("${q://QID15/ChoiceGroup/SelectedChoices/6}", "${q://QID15/SelectedAnswerRecode/6}"),
                pipedMatrixRow("${q://QID15/ChoiceGroup/SelectedChoices/7}", "${q://QID15/SelectedAnswerRecode/7}")
            ],
            stmt_texts: [
                pipedStrFirst("${q://QID15/AnswerGroup/ChoiceDescription/1}", "${q://QID15/AnswerGroup/DisplayedChoices/1}", "${q://QID15/ChoiceGroup/ChoiceDescription/1}", "${q://QID15/ChoiceGroup/DisplayedChoices/1}"),
                pipedStrFirst("${q://QID15/AnswerGroup/ChoiceDescription/2}", "${q://QID15/AnswerGroup/DisplayedChoices/2}", "${q://QID15/ChoiceGroup/ChoiceDescription/2}", "${q://QID15/ChoiceGroup/DisplayedChoices/2}"),
                pipedStrFirst("${q://QID15/AnswerGroup/ChoiceDescription/3}", "${q://QID15/AnswerGroup/DisplayedChoices/3}", "${q://QID15/ChoiceGroup/ChoiceDescription/3}", "${q://QID15/ChoiceGroup/DisplayedChoices/3}"),
                pipedStrFirst("${q://QID15/AnswerGroup/ChoiceDescription/4}", "${q://QID15/AnswerGroup/DisplayedChoices/4}", "${q://QID15/ChoiceGroup/ChoiceDescription/4}", "${q://QID15/ChoiceGroup/DisplayedChoices/4}"),
                pipedStrFirst("${q://QID15/AnswerGroup/ChoiceDescription/5}", "${q://QID15/AnswerGroup/DisplayedChoices/5}", "${q://QID15/ChoiceGroup/ChoiceDescription/5}", "${q://QID15/ChoiceGroup/DisplayedChoices/5}"),
                pipedStrFirst("${q://QID15/AnswerGroup/ChoiceDescription/6}", "${q://QID15/AnswerGroup/DisplayedChoices/6}", "${q://QID15/ChoiceGroup/ChoiceDescription/6}", "${q://QID15/ChoiceGroup/DisplayedChoices/6}"),
                pipedStrFirst("${q://QID15/AnswerGroup/ChoiceDescription/7}", "${q://QID15/AnswerGroup/DisplayedChoices/7}", "${q://QID15/ChoiceGroup/ChoiceDescription/7}", "${q://QID15/ChoiceGroup/DisplayedChoices/7}")
            ],
            feeling:    pipedLikert("${q://QID16/ChoiceGroup/SelectedChoices}"),
            importance: pipedLikertOrRecode("${q://QID17/ChoiceGroup/SelectedChoices}", "${q://QID17/ChoiceGroup/SelectedChoices/1}", "${q://QID17/SelectedAnswerRecode/1}")
        },

        'PERS_PE': {
            opinion: pipedLikertOrRecode("${q://QID83/ChoiceGroup/SelectedChoices/1}", "${q://QID83/ChoiceGroup/SelectedChoices}", "${q://QID83/SelectedAnswerRecode/1}"),
            reason: pipedStrFirst("${q://QID84/ChoiceTextEntryValue}", "${q://QID84/ChoiceTextEntryValue/1}", "${q://QID84/ChoiceTextEntryValue/2}"),
            stmts: [
                pipedMatrixRow("${q://QID85/ChoiceGroup/SelectedChoices/1}", "${q://QID85/SelectedAnswerRecode/1}"),
                pipedMatrixRow("${q://QID85/ChoiceGroup/SelectedChoices/2}", "${q://QID85/SelectedAnswerRecode/2}"),
                pipedMatrixRow("${q://QID85/ChoiceGroup/SelectedChoices/3}", "${q://QID85/SelectedAnswerRecode/3}"),
                pipedMatrixRow("${q://QID85/ChoiceGroup/SelectedChoices/4}", "${q://QID85/SelectedAnswerRecode/4}"),
                pipedMatrixRow("${q://QID85/ChoiceGroup/SelectedChoices/5}", "${q://QID85/SelectedAnswerRecode/5}"),
                pipedMatrixRow("${q://QID85/ChoiceGroup/SelectedChoices/6}", "${q://QID85/SelectedAnswerRecode/6}"),
                pipedMatrixRow("${q://QID85/ChoiceGroup/SelectedChoices/7}", "${q://QID85/SelectedAnswerRecode/7}")
            ],
            stmt_texts: [
                pipedStrFirst("${q://QID85/AnswerGroup/ChoiceDescription/1}", "${q://QID85/AnswerGroup/DisplayedChoices/1}", "${q://QID85/ChoiceGroup/ChoiceDescription/1}", "${q://QID85/ChoiceGroup/DisplayedChoices/1}"),
                pipedStrFirst("${q://QID85/AnswerGroup/ChoiceDescription/2}", "${q://QID85/AnswerGroup/DisplayedChoices/2}", "${q://QID85/ChoiceGroup/ChoiceDescription/2}", "${q://QID85/ChoiceGroup/DisplayedChoices/2}"),
                pipedStrFirst("${q://QID85/AnswerGroup/ChoiceDescription/3}", "${q://QID85/AnswerGroup/DisplayedChoices/3}", "${q://QID85/ChoiceGroup/ChoiceDescription/3}", "${q://QID85/ChoiceGroup/DisplayedChoices/3}"),
                pipedStrFirst("${q://QID85/AnswerGroup/ChoiceDescription/4}", "${q://QID85/AnswerGroup/DisplayedChoices/4}", "${q://QID85/ChoiceGroup/ChoiceDescription/4}", "${q://QID85/ChoiceGroup/DisplayedChoices/4}"),
                pipedStrFirst("${q://QID85/AnswerGroup/ChoiceDescription/5}", "${q://QID85/AnswerGroup/DisplayedChoices/5}", "${q://QID85/ChoiceGroup/ChoiceDescription/5}", "${q://QID85/ChoiceGroup/DisplayedChoices/5}"),
                pipedStrFirst("${q://QID85/AnswerGroup/ChoiceDescription/6}", "${q://QID85/AnswerGroup/DisplayedChoices/6}", "${q://QID85/ChoiceGroup/ChoiceDescription/6}", "${q://QID85/ChoiceGroup/DisplayedChoices/6}"),
                pipedStrFirst("${q://QID85/AnswerGroup/ChoiceDescription/7}", "${q://QID85/AnswerGroup/DisplayedChoices/7}", "${q://QID85/ChoiceGroup/ChoiceDescription/7}", "${q://QID85/ChoiceGroup/DisplayedChoices/7}")
            ],
            feeling:    pipedLikert("${q://QID86/ChoiceGroup/SelectedChoices}"),
            importance: pipedLikertOrRecode("${q://QID87/ChoiceGroup/SelectedChoices}", "${q://QID87/ChoiceGroup/SelectedChoices/1}", "${q://QID87/SelectedAnswerRecode/1}")
        },

        'CTRL_TEAMS': {
            opinion: pipedLikertOrRecode("${q://QID89/ChoiceGroup/SelectedChoices/1}", "${q://QID89/ChoiceGroup/SelectedChoices}", "${q://QID89/SelectedAnswerRecode/1}"),
            reason: pipedStrFirst("${q://QID90/ChoiceTextEntryValue}", "${q://QID90/ChoiceTextEntryValue/1}", "${q://QID90/ChoiceTextEntryValue/2}"),
            stmts: [
                pipedMatrixRow("${q://QID91/ChoiceGroup/SelectedChoices/1}", "${q://QID91/SelectedAnswerRecode/1}"),
                pipedMatrixRow("${q://QID91/ChoiceGroup/SelectedChoices/2}", "${q://QID91/SelectedAnswerRecode/2}"),
                pipedMatrixRow("${q://QID91/ChoiceGroup/SelectedChoices/3}", "${q://QID91/SelectedAnswerRecode/3}"),
                pipedMatrixRow("${q://QID91/ChoiceGroup/SelectedChoices/4}", "${q://QID91/SelectedAnswerRecode/4}"),
                pipedMatrixRow("${q://QID91/ChoiceGroup/SelectedChoices/5}", "${q://QID91/SelectedAnswerRecode/5}"),
                pipedMatrixRow("${q://QID91/ChoiceGroup/SelectedChoices/6}", "${q://QID91/SelectedAnswerRecode/6}"),
                pipedMatrixRow("${q://QID91/ChoiceGroup/SelectedChoices/7}", "${q://QID91/SelectedAnswerRecode/7}")
            ],
            stmt_texts: [
                pipedStrFirst("${q://QID91/AnswerGroup/ChoiceDescription/1}", "${q://QID91/AnswerGroup/DisplayedChoices/1}", "${q://QID91/ChoiceGroup/ChoiceDescription/1}", "${q://QID91/ChoiceGroup/DisplayedChoices/1}"),
                pipedStrFirst("${q://QID91/AnswerGroup/ChoiceDescription/2}", "${q://QID91/AnswerGroup/DisplayedChoices/2}", "${q://QID91/ChoiceGroup/ChoiceDescription/2}", "${q://QID91/ChoiceGroup/DisplayedChoices/2}"),
                pipedStrFirst("${q://QID91/AnswerGroup/ChoiceDescription/3}", "${q://QID91/AnswerGroup/DisplayedChoices/3}", "${q://QID91/ChoiceGroup/ChoiceDescription/3}", "${q://QID91/ChoiceGroup/DisplayedChoices/3}"),
                pipedStrFirst("${q://QID91/AnswerGroup/ChoiceDescription/4}", "${q://QID91/AnswerGroup/DisplayedChoices/4}", "${q://QID91/ChoiceGroup/ChoiceDescription/4}", "${q://QID91/ChoiceGroup/DisplayedChoices/4}"),
                pipedStrFirst("${q://QID91/AnswerGroup/ChoiceDescription/5}", "${q://QID91/AnswerGroup/DisplayedChoices/5}", "${q://QID91/ChoiceGroup/ChoiceDescription/5}", "${q://QID91/ChoiceGroup/DisplayedChoices/5}"),
                pipedStrFirst("${q://QID91/AnswerGroup/ChoiceDescription/6}", "${q://QID91/AnswerGroup/DisplayedChoices/6}", "${q://QID91/ChoiceGroup/ChoiceDescription/6}", "${q://QID91/ChoiceGroup/DisplayedChoices/6}"),
                pipedStrFirst("${q://QID91/AnswerGroup/ChoiceDescription/7}", "${q://QID91/AnswerGroup/DisplayedChoices/7}", "${q://QID91/ChoiceGroup/ChoiceDescription/7}", "${q://QID91/ChoiceGroup/DisplayedChoices/7}")
            ],
            feeling:    pipedLikert("${q://QID92/ChoiceGroup/SelectedChoices}"),
            importance: pipedLikertOrRecode("${q://QID93/ChoiceGroup/SelectedChoices}", "${q://QID93/ChoiceGroup/SelectedChoices/1}", "${q://QID93/SelectedAnswerRecode/1}")
        },

        'CTRL_PLASTIC': {
            opinion: pipedLikertOrRecode("${q://QID94/ChoiceGroup/SelectedChoices/1}", "${q://QID94/ChoiceGroup/SelectedChoices}", "${q://QID94/SelectedAnswerRecode/1}"),
            reason: pipedStrFirst("${q://QID95/ChoiceTextEntryValue}", "${q://QID95/ChoiceTextEntryValue/1}", "${q://QID95/ChoiceTextEntryValue/2}"),
            stmts: [
                pipedMatrixRow("${q://QID96/ChoiceGroup/SelectedChoices/1}", "${q://QID96/SelectedAnswerRecode/1}"),
                pipedMatrixRow("${q://QID96/ChoiceGroup/SelectedChoices/2}", "${q://QID96/SelectedAnswerRecode/2}"),
                pipedMatrixRow("${q://QID96/ChoiceGroup/SelectedChoices/3}", "${q://QID96/SelectedAnswerRecode/3}"),
                pipedMatrixRow("${q://QID96/ChoiceGroup/SelectedChoices/4}", "${q://QID96/SelectedAnswerRecode/4}"),
                pipedMatrixRow("${q://QID96/ChoiceGroup/SelectedChoices/5}", "${q://QID96/SelectedAnswerRecode/5}"),
                pipedMatrixRow("${q://QID96/ChoiceGroup/SelectedChoices/6}", "${q://QID96/SelectedAnswerRecode/6}"),
                pipedMatrixRow("${q://QID96/ChoiceGroup/SelectedChoices/7}", "${q://QID96/SelectedAnswerRecode/7}")
            ],
            stmt_texts: [
                pipedStrFirst("${q://QID96/AnswerGroup/ChoiceDescription/1}", "${q://QID96/AnswerGroup/DisplayedChoices/1}", "${q://QID96/ChoiceGroup/ChoiceDescription/1}", "${q://QID96/ChoiceGroup/DisplayedChoices/1}"),
                pipedStrFirst("${q://QID96/AnswerGroup/ChoiceDescription/2}", "${q://QID96/AnswerGroup/DisplayedChoices/2}", "${q://QID96/ChoiceGroup/ChoiceDescription/2}", "${q://QID96/ChoiceGroup/DisplayedChoices/2}"),
                pipedStrFirst("${q://QID96/AnswerGroup/ChoiceDescription/3}", "${q://QID96/AnswerGroup/DisplayedChoices/3}", "${q://QID96/ChoiceGroup/ChoiceDescription/3}", "${q://QID96/ChoiceGroup/DisplayedChoices/3}"),
                pipedStrFirst("${q://QID96/AnswerGroup/ChoiceDescription/4}", "${q://QID96/AnswerGroup/DisplayedChoices/4}", "${q://QID96/ChoiceGroup/ChoiceDescription/4}", "${q://QID96/ChoiceGroup/DisplayedChoices/4}"),
                pipedStrFirst("${q://QID96/AnswerGroup/ChoiceDescription/5}", "${q://QID96/AnswerGroup/DisplayedChoices/5}", "${q://QID96/ChoiceGroup/ChoiceDescription/5}", "${q://QID96/ChoiceGroup/DisplayedChoices/5}"),
                pipedStrFirst("${q://QID96/AnswerGroup/ChoiceDescription/6}", "${q://QID96/AnswerGroup/DisplayedChoices/6}", "${q://QID96/ChoiceGroup/ChoiceDescription/6}", "${q://QID96/ChoiceGroup/DisplayedChoices/6}"),
                pipedStrFirst("${q://QID96/AnswerGroup/ChoiceDescription/7}", "${q://QID96/AnswerGroup/DisplayedChoices/7}", "${q://QID96/ChoiceGroup/ChoiceDescription/7}", "${q://QID96/ChoiceGroup/DisplayedChoices/7}")
            ],
            feeling:    pipedLikert("${q://QID97/ChoiceGroup/SelectedChoices}"),
            importance: pipedLikertOrRecode("${q://QID98/ChoiceGroup/SelectedChoices}", "${q://QID98/ChoiceGroup/SelectedChoices/1}", "${q://QID98/SelectedAnswerRecode/1}")
        },

        // Matrix Q102: rows /1-/7. Q104 is ChoiceTextEntryValue in your survey — not used here.
        // Feeling/importance: Q103 and Q101 (verify in Survey Flow if these swap).
        'CTRL_PE': {
            opinion: pipedLikertOrRecode("${q://QID99/ChoiceGroup/SelectedChoices/1}", "${q://QID99/ChoiceGroup/SelectedChoices}", "${q://QID99/SelectedAnswerRecode/1}"),
            reason: pipedStrFirst("${q://QID100/ChoiceTextEntryValue}", "${q://QID100/ChoiceTextEntryValue/1}", "${q://QID100/ChoiceTextEntryValue/2}"),
            stmts: [
                pipedMatrixRow("${q://QID102/ChoiceGroup/SelectedChoices/1}", "${q://QID102/SelectedAnswerRecode/1}"),
                pipedMatrixRow("${q://QID102/ChoiceGroup/SelectedChoices/2}", "${q://QID102/SelectedAnswerRecode/2}"),
                pipedMatrixRow("${q://QID102/ChoiceGroup/SelectedChoices/3}", "${q://QID102/SelectedAnswerRecode/3}"),
                pipedMatrixRow("${q://QID102/ChoiceGroup/SelectedChoices/4}", "${q://QID102/SelectedAnswerRecode/4}"),
                pipedMatrixRow("${q://QID102/ChoiceGroup/SelectedChoices/5}", "${q://QID102/SelectedAnswerRecode/5}"),
                pipedMatrixRow("${q://QID102/ChoiceGroup/SelectedChoices/6}", "${q://QID102/SelectedAnswerRecode/6}"),
                pipedMatrixRow("${q://QID102/ChoiceGroup/SelectedChoices/7}", "${q://QID102/SelectedAnswerRecode/7}")
            ],
            stmt_texts: [
                pipedStrFirst("${q://QID102/AnswerGroup/ChoiceDescription/1}", "${q://QID102/AnswerGroup/DisplayedChoices/1}", "${q://QID102/ChoiceGroup/ChoiceDescription/1}", "${q://QID102/ChoiceGroup/DisplayedChoices/1}"),
                pipedStrFirst("${q://QID102/AnswerGroup/ChoiceDescription/2}", "${q://QID102/AnswerGroup/DisplayedChoices/2}", "${q://QID102/ChoiceGroup/ChoiceDescription/2}", "${q://QID102/ChoiceGroup/DisplayedChoices/2}"),
                pipedStrFirst("${q://QID102/AnswerGroup/ChoiceDescription/3}", "${q://QID102/AnswerGroup/DisplayedChoices/3}", "${q://QID102/ChoiceGroup/ChoiceDescription/3}", "${q://QID102/ChoiceGroup/DisplayedChoices/3}"),
                pipedStrFirst("${q://QID102/AnswerGroup/ChoiceDescription/4}", "${q://QID102/AnswerGroup/DisplayedChoices/4}", "${q://QID102/ChoiceGroup/ChoiceDescription/4}", "${q://QID102/ChoiceGroup/DisplayedChoices/4}"),
                pipedStrFirst("${q://QID102/AnswerGroup/ChoiceDescription/5}", "${q://QID102/AnswerGroup/DisplayedChoices/5}", "${q://QID102/ChoiceGroup/ChoiceDescription/5}", "${q://QID102/ChoiceGroup/DisplayedChoices/5}"),
                pipedStrFirst("${q://QID102/AnswerGroup/ChoiceDescription/6}", "${q://QID102/AnswerGroup/DisplayedChoices/6}", "${q://QID102/ChoiceGroup/ChoiceDescription/6}", "${q://QID102/ChoiceGroup/DisplayedChoices/6}"),
                pipedStrFirst("${q://QID102/AnswerGroup/ChoiceDescription/7}", "${q://QID102/AnswerGroup/DisplayedChoices/7}", "${q://QID102/ChoiceGroup/ChoiceDescription/7}", "${q://QID102/ChoiceGroup/DisplayedChoices/7}")
            ],
            feeling:    pipedLikert("${q://QID103/ChoiceGroup/SelectedChoices}"),
            importance: pipedLikertOrRecode("${q://QID101/ChoiceGroup/SelectedChoices}", "${q://QID101/ChoiceGroup/SelectedChoices/1}", "${q://QID101/SelectedAnswerRecode/1}")
        }
    };

    var activeBlock = preBlockId ? (allBlocks[preBlockId] || null) : null;
    console.log('[survey1] Active block selection', { preBlockId: preBlockId, hasActiveBlock: !!activeBlock });

    if (!activeBlock && preBlockId) {
        console.error('No block data found for pre_block_id: ' + preBlockId);
    }

    var blockResponses = null;
    if (activeBlock) {
        var stmtTextsForPayload = activeBlock.stmt_texts ? activeBlock.stmt_texts.slice() : null;
        if (stmtTextsForPayload && stmtTextsForPayload.length === 7) {
            var s0 = stmtTextsForPayload[0];
            var allStmtTextSame = true;
            for (var si = 1; si < 7; si++) {
                if (stmtTextsForPayload[si] !== s0) {
                    allStmtTextSame = false;
                    break;
                }
            }
            if (allStmtTextSame && s0) {
                var s0l = String(s0).toLowerCase();
                if (s0l.indexOf('not at all') !== -1 && s0l.indexOf('very strongly') !== -1) {
                    stmtTextsForPayload = [null, null, null, null, null, null, null];
                } else {
                    var split7 = trySplitSevenCommaSeparatedStatements(String(s0));
                    if (split7) {
                        stmtTextsForPayload = split7;
                    }
                }
            }
        }

        var statementsDetailed = [];
        for (var i = 0; i < activeBlock.stmts.length; i++) {
            if (activeBlock.stmts[i] !== null) {
                statementsDetailed.push({
                    statement_id: 'stmt' + (i + 1),
                    statement_text: stmtTextsForPayload ? stmtTextsForPayload[i] : null,
                    response: activeBlock.stmts[i],
                    response_label: likertAgreeLabel(activeBlock.stmts[i])
                });
            }
        }

        blockResponses = {
            opinion: activeBlock.opinion,
            opinion_label: likertAgreeLabel(activeBlock.opinion),
            opinion_reason: activeBlock.reason,
            statements: statementsDetailed.length === 7 ? statementsDetailed : null,
            feeling_strength: activeBlock.feeling,
            topic_importance: activeBlock.importance
        };

        console.log('[survey1] Block responses resolved', blockResponses);
    }

    var payload = {
        participant_id: participantId,
        prolific_id: prolificId,
        qualtrics_response_id: qualtricsResponseId,
        topic_condition: topicCondition,
        topic_usage: topicUsage,
        topic_behavior: topicBehavior,
        pre_block_id: preBlockId,
        pre_topic: preTopic,
        pre_personalization: prePersonalization,
        pre_is_control: preIsControl,
        block_responses: blockResponses,
        demographics: Object.keys(demographics).length > 0 ? demographics : null,
        survey_comment: surveyComment,
        survey_completion_time: new Date().toISOString()
    };

    console.log('[survey1] Sending survey data to API:', JSON.stringify(payload, null, 2));
    console.log('[survey1] POST', { url: API_URL });

    var survey1PostKey = 'survey1_api_post_' + participantId;
    if (window[survey1PostKey]) {
        console.log('[survey1] Skipping duplicate POST (already sent for this response). Put this script on one question only.');
        return;
    }
    window[survey1PostKey] = true;

    fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(function(response) {
        console.log('[survey1] Response status', { ok: response.ok, status: response.status });
        if (!response.ok) {
            throw new Error('HTTP error! status: ' + response.status);
        }
        return response.json();
    })
    .then(function(data) {
        console.log('Survey data sent successfully:', data);
        Qualtrics.SurveyEngine.setEmbeddedData('api_response_status', 'success');
        Qualtrics.SurveyEngine.setEmbeddedData('api_survey_id', data.survey_id);
        Qualtrics.SurveyEngine.setEmbeddedData('api_timestamp', data.timestamp);
    })
    .catch(function(error) {
        console.error('Error sending survey data:', error);
        Qualtrics.SurveyEngine.setEmbeddedData('api_response_status', 'error');
        Qualtrics.SurveyEngine.setEmbeddedData('api_error', error.toString());
    });

});

-- DEPRECATED — kept as a stub so the numbered build sequence (00→10) stays unbroken.
-- Original purpose: hybrid LLM + rule trust via single-model LEFT JOIN.
-- Replaced by: 10_two_model_verify.sql (rebuilds gold_trust_final using two-model
-- blended scores from gold_trust_llm + gold_trust_llm_v2 with conservative LEAST on disagreement).
--
-- Do NOT run this file. Running 10_two_model_verify.sql alone produces the correct gold_trust_final.
SELECT 'noop — see 10_two_model_verify.sql' AS deprecation_note;

"""
evaluation/ragas_eval.py
─────────────────────────────────────────────────────────
ارزیابی pipeline با RAGAS — چهار متریک اصلی:
  - Faithfulness:       جواب فقط از context اومده؟
  - Answer Relevancy:   جواب به سوال مرتبطه؟
  - Context Precision:  chunk های retrieve‌شده واقعاً مفیدن؟
  - Context Recall:     همه اطلاعات لازم retrieve شدن؟
─────────────────────────────────────────────────────────
"""

import json
import numpy as np
from ragas import evaluate, EvaluationDataset, SingleTurnSample
from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas.run_config import RunConfig

import config
from main import process_query
from generation.generator import generate_answer


TEST_SET = [
    {
        "question": "How do I install the duplexer on the RD982S?",
        "ground_truth": "To install the duplexer, mount it on the exciter "
                        "module and receiver module of the repeater, then "
                        "fasten it with the two screws inside the housing "
                        "and the two screws on the side of the housing."
    },
    {
        "question": "What should I check after installation is complete?",
        "ground_truth": "After installation, power on the repeater and check "
                        "whether it works properly by observing the nine LED "
                        "indicators and the LCD display in the front panel."
    },
    {
        "question": "What is the operating temperature range of the RD982S?",
        "ground_truth": "The operating temperature range for installation "
                        "environment is -30 degrees Celsius to +60 degrees "
                        "Celsius with relative humidity of 95 percent."
    },
    {
        "question": "What tools are needed for installation?",
        "ground_truth": "The tools required for installation are a Phillips "
                        "screwdriver, a T-10 torx screwdriver, and a spanner."
    },
    {
        "question": "What does it mean when the alarm indicator glows red?",
        "ground_truth": "When the alarm indicator glows red, it signals an "
                        "alarm condition such as low forward power, TX/RX "
                        "unlock, fan failure, over temperature, or over/low "
                        "voltage."
    },
    {
        "question": "How do I turn off the repeater?",
        "ground_truth": "To turn off the repeater, use the power switch to "
                        "power it off as described in the Basic Operations "
                        "section on Turning the Repeater On or Off."
    },
    {
        "question": "Where is the ground screw located on the RD982S?",
        "ground_truth": "The ground screw is located on the rear panel of "
                        "the repeater."
    },
    {
        "question": "What voltage does the RD982S require?",
        "ground_truth": "The RD982S requires a DC power supply voltage of "
                        "13.6V with plus or minus 15 percent tolerance."
    },
    {
        "question": "What should I do if the VSWR alarm is triggered?",
        "ground_truth": "If the VSWR alarm is triggered, check the connection "
                        "between the repeater and RF cable or antenna/feed "
                        "line for loose or damaged connections, and secure or "
                        "replace as needed."
    },
    {
        "question": "What location types are suitable for installing the repeater?",
        "ground_truth": "The repeater can be installed in a rack, bracket, "
                        "or cabinet, or on a desk, in a dry and well-ventilated "
                        "place."
    },
]


def _safe_score(value) -> float:
    """
    RAGAS گاهی یه list برمیگردونه (یه score به ازای هر sample).
    این تابع به صورت امن میانگینش رو حساب میکنه.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        valid = [v for v in value if v is not None and not (isinstance(v, float) and np.isnan(v))]
        return float(np.mean(valid)) if valid else 0.0
    return 0.0


def run_evaluation(model_name: str) -> dict:
    print(f"\n{'='*60}")
    print(f"Evaluating model: {model_name}")
    print(f"{'='*60}")

    samples = []

    for i, case in enumerate(TEST_SET):
        print(f"  Processing {i+1}/{len(TEST_SET)}: {case['question'][:50]}...")

        try:
            retrieval = process_query(case["question"])
            generation = generate_answer(
                case["question"],
                retrieval["chunks"],
                model=model_name
            )

            retrieved_contexts = [
                c.payload.get("text", "") for c in retrieval["chunks"]
            ]

            sample = SingleTurnSample(
                user_input=case["question"],
                response=generation["answer"],
                retrieved_contexts=retrieved_contexts,
                reference=case["ground_truth"]
            )
            samples.append(sample)

        except Exception as e:
            print(f"    Error on sample {i+1}: {e}")
            continue

    if not samples:
        print("No samples collected!")
        return {}

    dataset = EvaluationDataset(samples=samples)

    # timeout رو بالا میبریم چون مدل‌های محلی کند هستن
    ragas_llm = LangchainLLMWrapper(ChatOpenAI(
        base_url=f"{config.LITELLM_BASE_URL}/v1",
        api_key=config.LITELLM_API_KEY,
        model=model_name,
        timeout=120,
        max_retries=1
    ))

    ragas_embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(
        base_url=f"{config.LITELLM_BASE_URL}/v1",
        api_key=config.LITELLM_API_KEY,
        model=config.MODEL_EMBEDDING,
        check_embedding_ctx_length=False
    ))

    metrics = [
        Faithfulness(llm=ragas_llm),
        AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings),
        ContextPrecision(llm=ragas_llm),
        ContextRecall(llm=ragas_llm),
    ]

    print(f"\n  Running RAGAS evaluation ({len(samples)} samples)...")

    run_config = RunConfig(timeout=300, max_retries=1, max_wait=60)

    results = evaluate(
        dataset=dataset,
        metrics=metrics,
        raise_exceptions=False,
        run_config=run_config
    )


    scores = {
        "model": model_name,
        "samples": len(samples),
        "faithfulness": round(_safe_score(results["faithfulness"]), 4),
        "answer_relevancy": round(_safe_score(results["answer_relevancy"]), 4),
        "context_precision": round(_safe_score(results["context_precision"]), 4),
        "context_recall": round(_safe_score(results["context_recall"]), 4),
    }
    scores["average"] = round(
        sum([scores["faithfulness"], scores["answer_relevancy"],
             scores["context_precision"], scores["context_recall"]]) / 4, 4
    )

    return scores

def print_results(all_results: list):
    valid = [r for r in all_results if r and "model" in r]
    if not valid:
        print("No valid results to display.")
        return

    print(f"\n{'='*70}")
    print("RAGAS BENCHMARK RESULTS")
    print(f"{'='*70}")
    print(f"{'Model':<20} {'Faith':>8} {'Rel':>8} {'Prec':>8} {'Recall':>8} {'Avg':>8}")
    print(f"{'-'*70}")

    for r in valid:
        print(f"{r['model']:<20} "
              f"{r['faithfulness']:>8.4f} "
              f"{r['answer_relevancy']:>8.4f} "
              f"{r['context_precision']:>8.4f} "
              f"{r['context_recall']:>8.4f} "
              f"{r['average']:>8.4f}")

    print(f"{'='*70}")

    best = max(valid, key=lambda x: x["average"])
    print(f"\nBest overall: {best['model']} (avg={best['average']})")



if __name__ == "__main__":
    models_to_test = [
        config.MODEL_LLAMA,
        config.MODEL_QWEN,
        config.MODEL_DEEPSEEK,
    ]

    all_results = []

    for model in models_to_test:
        try:
            result = run_evaluation(model)
            if result:
                all_results.append(result)
                print(f"\n  Results for {model}:")
                for k, v in result.items():
                    if k not in ("model", "samples"):
                        print(f"    {k}: {v}")
        except Exception as e:
            print(f"Failed to evaluate {model}: {e}")

    if all_results:
        print_results(all_results)

        output_path = "evaluation/benchmark_results.json"
        with open(output_path, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nResults saved to {output_path}")
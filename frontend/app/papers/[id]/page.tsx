"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  useCallback,
  useEffect,
  useState,
  type KeyboardEvent,
} from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeftCircle,
  Database,
  ExternalLink,
  FileText,
  FlaskConical,
  Lightbulb,
  Search,
  Sparkles,
  Tag,
  Target,
} from "lucide-react";

import { AppShell } from "@/components/layout/app_shell";
import {
  askPaper,
  extractPaper,
  getExtraction,
  getPaper,
  parsePaper,
  searchGlobalLiterature,
  searchPaper,
  type ExtractionResponse,
} from "@/lib/api";
import type {
  AnswerSource,
  ChunkResult,
  Extraction,
  Paper,
  PaperMetadata,
} from "@/lib/types";


type SearchPaperResponse =
  | ChunkResult[]
  | {
      query?: string;
      top_k?: number;
      count?: number;
      results?: ChunkResult[];
    };


function getErrorMessage(
  error: unknown,
  fallback: string
): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}


function normalizeExtraction(
  data: ExtractionResponse | null
): Extraction | null {
  if (!data) {
    return null;
  }

  if (
    typeof data === "object" &&
    data !== null &&
    "extraction" in data
  ) {
    return data.extraction || null;
  }

  return data as Extraction;
}


function normalizeSearchResults(
  data: SearchPaperResponse,
): ChunkResult[] {
  if (Array.isArray(data)) {
    return data;
  }

  if (
    data &&
    typeof data === "object" &&
    Array.isArray(data.results)
  ) {
    return data.results;
  }

  return [];
}


function textValue(
  value: string | string[] | null | undefined,
): string {
  if (Array.isArray(value)) {
    return value
      .filter(Boolean)
      .join(", ")
      .trim();
  }

  return typeof value === "string"
    ? value.trim()
    : "";
}


/* =========================================================
   RECOMMENDATION QUERY
   ========================================================= */

function buildRecommendationQuery(
  paper: Paper,
  extraction: Extraction
): string {
  const data = extraction as Record<string, unknown>;

  const objective =
    typeof data.objective === "string"
      ? data.objective
      : "";

  const methodology =
    typeof data.methodology === "string"
      ? data.methodology
      : "";

  const dataset =
    typeof data.dataset === "string"
      ? data.dataset
      : "";

  const evaluationMetric =
    typeof data.evaluation_metric === "string"
      ? data.evaluation_metric
      : "";

  const keywordsValue = data.keywords;

  const stopWords = new Set([
    "this",
    "that",
    "these",
    "those",
    "using",
    "used",
    "based",
    "paper",
    "study",
    "research",
    "method",
    "methods",
    "approach",
    "model",
    "models",
    "data",
    "dataset",
    "results",
    "result",
    "performance",
    "evaluate",
    "evaluated",
    "evaluation",
    "analysis",
    "classification",
    "classify",
    "developed",
    "develop",
    "investigate",
    "investigating",
    "explore",
    "exploring",
    "assess",
    "assessing",
    "high",
    "limited",
    "limitedly",
    "application",
    "applications",
    "proposed",
    "propose",
    "shows",
    "shown",
    "provide",
    "provides",
    "achieve",
    "achieved",
    "accuracy",
    "f1",
    "score",
  ]);

  const extractConcepts = (
    value: string,
    maxTerms: number
  ): string[] => {
    const words = value
      .toLowerCase()
      .replace(/[^a-zA-Z0-9\s-]/g, " ")
      .split(/\s+/)
      .filter(Boolean);

    const concepts: string[] = [];

    for (const word of words) {
      const cleaned = word.trim();

      if (
        cleaned.length < 4 ||
        stopWords.has(cleaned) ||
        concepts.includes(cleaned)
      ) {
        continue;
      }

      concepts.push(cleaned);

      if (concepts.length >= maxTerms) {
        break;
      }
    }

    return concepts;
  };

  const titleConcepts = extractConcepts(
    paper.title || "",
    5
  );

  const objectiveConcepts = extractConcepts(
    objective,
    6
  );

  const datasetConcepts = extractConcepts(
    dataset,
    6
  );

  const methodologyConcepts = extractConcepts(
    methodology,
    7
  );

  const metricConcepts = extractConcepts(
    evaluationMetric,
    2
  );

  let keywordConcepts: string[] = [];

  if (Array.isArray(keywordsValue)) {
    keywordConcepts = keywordsValue
      .filter(
        (value): value is string =>
          typeof value === "string"
      )
      .flatMap((value) =>
        extractConcepts(value, 2)
      );
  } else if (
    typeof keywordsValue === "string"
  ) {
    keywordConcepts = extractConcepts(
      keywordsValue,
      6
    );
  }

  const phrases: string[] = [];

  const objectiveLower =
    objective.toLowerCase();

  const methodologyLower =
    methodology.toLowerCase();

  const datasetLower =
    dataset.toLowerCase();

  const titleLower =
    (paper.title || "").toLowerCase();

  if (
    objectiveLower.includes("exoplanet") ||
    titleLower.includes("exoplanet")
  ) {
    phrases.push("exoplanet detection");
  }

  if (
    datasetLower.includes("kepler") ||
    titleLower.includes("kepler")
  ) {
    phrases.push("Kepler");
  }

  if (
    methodologyLower.includes(
      "machine learning"
    ) ||
    titleLower.includes(
      "machine learning"
    )
  ) {
    phrases.push("machine learning");
  }

  if (
    datasetLower.includes(
      "light curve"
    ) ||
    datasetLower.includes(
      "light-curve"
    ) ||
    objectiveLower.includes(
      "light intensity"
    ) ||
    titleLower.includes(
      "light intensity"
    )
  ) {
    phrases.push("stellar light curves");
  }

  if (
    methodologyLower.includes("knn")
  ) {
    phrases.push("KNN");
  }

  if (
    methodologyLower.includes(
      "logistic regression"
    )
  ) {
    phrases.push(
      "logistic regression"
    );
  }

  if (
    methodologyLower.includes(
      "decision tree"
    )
  ) {
    phrases.push("decision tree");
  }

  if (
    methodologyLower.includes("smote")
  ) {
    phrases.push("SMOTE");
  }

  const combined = [
    ...phrases,
    ...titleConcepts,
    ...objectiveConcepts,
    ...datasetConcepts,
    ...methodologyConcepts,
    ...keywordConcepts,
    ...metricConcepts,
  ];

  const unique = [
    ...new Set(
      combined
        .map((item) => item.trim())
        .filter(Boolean)
    ),
  ];

  return unique.join(" ").slice(0, 280);
}

/* =========================================================
   RECOMMENDATION HELPERS
   ========================================================= */

function isLikelyEnglishTitle(
  title: string
): boolean {
  const cleaned = title.replace(
    /\s/g,
    ""
  );

  if (!cleaned) {
    return false;
  }

  const latinCharacters =
    cleaned.match(/[A-Za-zÀ-ÿ]/g)
      ?.length || 0;

  const nonLatinCharacters =
    cleaned.match(
      /[^\x00-\x7FÀ-ÿ]/g
    )?.length || 0;

  if (
    nonLatinCharacters > 0 &&
    latinCharacters /
      Math.max(cleaned.length, 1) <
      0.55
  ) {
    return false;
  }

  return true;
}

function normalizeTitle(
  title: string
): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function getQueryTerms(
  query: string
): string[] {
  const stopWords = new Set([
    "this",
    "that",
    "these",
    "those",
    "with",
    "from",
    "using",
    "used",
    "into",
    "their",
    "they",
    "them",
    "were",
    "have",
    "has",
    "been",
    "being",
    "which",
    "where",
    "when",
    "than",
    "such",
    "also",
    "paper",
    "study",
    "research",
    "method",
    "methods",
    "approach",
    "based",
    "results",
    "result",
    "data",
    "dataset",
    "model",
    "models",
    "performance",
    "analysis",
    "using",
    "proposed",
    "developed",
    "development",
    "investigate",
    "investigates",
    "investigating",
    "explore",
    "explores",
    "exploring",
    "assess",
    "assessing",
    "evaluate",
    "evaluated",
    "evaluation",
    "score",
    "accuracy",
  ]);

  const tokens = query
    .toLowerCase()
    .split(
      /[\s,.;:()[\]{}"'!?/\\|_+-]+/
    )
    .filter(Boolean);

  return [
    ...new Set(
      tokens.filter(
        (word) =>
          word.length >= 4 &&
          !stopWords.has(word) &&
          /^[a-z0-9]+$/.test(word)
      )
    ),
  ];
}

function getRecommendationReason(
  paper: PaperMetadata,
  query: string
): string {
  const title =
    paper.title?.toLowerCase() || "";

  const abstract =
    paper.abstract?.toLowerCase() || "";

  const queryTerms =
    getQueryTerms(query);

  const titleMatches = queryTerms.filter(
    (term) => title.includes(term)
  );

  const abstractMatches = queryTerms.filter(
    (term) =>
      !title.includes(term) &&
      abstract.includes(term)
  );

  const uniqueTitleMatches = [
    ...new Set(titleMatches),
  ].slice(0, 3);

  const uniqueAbstractMatches = [
    ...new Set(abstractMatches),
  ].slice(0, 3);

  if (uniqueTitleMatches.length >= 3) {
    return `Directly related to your research, with a similar focus on ${uniqueTitleMatches.join(
      ", "
    )}.`;
  }

  if (uniqueTitleMatches.length === 2) {
    return `Closely related through its focus on ${uniqueTitleMatches[0]} and ${uniqueTitleMatches[1]}.`;
  }

  if (uniqueTitleMatches.length === 1) {
    if (uniqueAbstractMatches.length > 0) {
      return `Shares a direct focus on ${uniqueTitleMatches[0]}, with additional overlap in ${uniqueAbstractMatches[0]}.`;
    }

    return `Shares a direct research focus on ${uniqueTitleMatches[0]}.`;
  }

  if (uniqueAbstractMatches.length >= 3) {
    return `Related through several research concepts, including ${uniqueAbstractMatches.join(
      ", "
    )}.`;
  }

  if (uniqueAbstractMatches.length === 2) {
    return `Related through shared concepts around ${uniqueAbstractMatches[0]} and ${uniqueAbstractMatches[1]}.`;
  }

  if (uniqueAbstractMatches.length === 1) {
    return `Related through its research focus on ${uniqueAbstractMatches[0]}.`;
  }

  return "Selected as related literature based on the research topic and concepts extracted from your paper.";
}

function getAuthors(
  paper: PaperMetadata
): string {
  if (!paper.authors) {
    return "Authors unavailable";
  }

  if (Array.isArray(paper.authors)) {
    return paper.authors
      .slice(0, 4)
      .join(", ");
  }

  return String(paper.authors);
}

function getPaperUrl(
  paper: PaperMetadata
): string | undefined {
  return (
    paper.pdf_url ||
    paper.url ||
    undefined
  );
}

/* =========================================================
   PAGE
   ========================================================= */

export default function PaperDetailPage() {
  const params =
    useParams<{ id: string }>();

  const id = params?.id;

  const [paper, setPaper] =
    useState<Paper | null>(null);

  const [extraction, setExtraction] =
    useState<Extraction | null>(null);

  const [results, setResults] =
    useState<ChunkResult[]>([]);

  const [query, setQuery] =
    useState("");

  const [answer, setAnswer] =
    useState("");

  const [answerSources, setAnswerSources] =
    useState<AnswerSource[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [searching, setSearching] =
    useState(false);

  const [answering, setAnswering] =
    useState(false);

  const [parsing, setParsing] =
    useState(false);

  const [extracting, setExtracting] =
    useState(false);

  const [recommendations, setRecommendations] =
    useState<PaperMetadata[]>([]);

  const [
    recommendationLoading,
    setRecommendationLoading,
  ] = useState(false);

  const [
    recommendationQuery,
    setRecommendationQuery,
  ] = useState("");

  const [
    recommendationPaperId,
    setRecommendationPaperId,
  ] = useState<string | null>(null);

  const [errorText, setErrorText] =
    useState("");

  /* =======================================================
     GENERATE RECOMMENDATIONS
     ======================================================= */

  const generateRecommendations =
    useCallback(
      async (
        currentPaper: Paper,
        currentExtraction: Extraction
      ) => {
        if (!currentPaper.id) {
          return;
        }

        try {
          setRecommendationLoading(
            true
          );

          setRecommendations([]);

          setRecommendationPaperId(
            currentPaper.id
          );

          const researchQuery =
            buildRecommendationQuery(
              currentPaper,
              currentExtraction
            );

          if (!researchQuery.trim()) {
            console.warn(
              "No research concepts available for recommendations."
            );
            return;
          }

          console.log(
            "[Recommendations] Query:",
            researchQuery
          );

          setRecommendationQuery(
            researchQuery
          );

          const related =
            await searchGlobalLiterature(
              researchQuery,
              8
            );

          const currentTitle =
            normalizeTitle(
              currentPaper.title || ""
            );

          const seen = new Set<string>();

          const filtered =
            related.filter(
              (recommended) => {
                const title =
                  recommended.title?.trim() ||
                  "";

                if (!title) {
                  return false;
                }

                if (
                  !isLikelyEnglishTitle(
                    title
                  )
                ) {
                  return false;
                }

                const normalized =
                  normalizeTitle(title);

                if (!normalized) {
                  return false;
                }

                if (
                  currentTitle &&
                  normalized === currentTitle
                ) {
                  return false;
                }

                if (
                  seen.has(normalized)
                ) {
                  return false;
                }

                seen.add(normalized);

                return true;
              }
            );

          setRecommendations(
            filtered.slice(0, 8)
          );
        } catch (error) {
          console.error(
            "Recommendation generation failed:",
            error
          );

          setRecommendations([]);
        } finally {
          setRecommendationLoading(
            false
          );
        }
      },
      []
    );

  /* =======================================================
     LOAD PAPER
     ======================================================= */

  const loadPaper =
    useCallback(async () => {
      if (!id) {
        return;
      }

      try {
        setLoading(true);
        setErrorText("");

        const [
          paperData,
          extractionData,
        ] = await Promise.all([
          getPaper(id),
          getExtraction(id).catch(
            () => null
          ),
        ]);

        const nextExtraction =
          normalizeExtraction(
            extractionData
          );

        setPaper(paperData);
        setExtraction(nextExtraction);

        if (
          nextExtraction &&
          paperData.status ===
            "extracted" &&
          recommendationPaperId !==
            paperData.id
        ) {
          void generateRecommendations(
            paperData,
            nextExtraction
          );
        }
      } catch (error) {
        console.error(
          "Failed to load paper:",
          error
        );

        setErrorText(
          getErrorMessage(
            error,
            "Failed to load the paper."
          )
        );
      } finally {
        setLoading(false);
      }
    }, [
      id,
      generateRecommendations,
      recommendationPaperId,
    ]);

  useEffect(() => {
    void loadPaper();
  }, [loadPaper]);

  /* =======================================================
     PARSE
     ======================================================= */

  async function handleParse() {
    if (
      !id ||
      parsing ||
      extracting
    ) {
      return;
    }

    try {
      setParsing(true);
      setErrorText("");

      await parsePaper(id);

      await loadPaper();
    } catch (error) {
      console.error(
        "Parsing failed:",
        error
      );

      setErrorText(
        getErrorMessage(
          error,
          "Parsing failed."
        )
      );
    } finally {
      setParsing(false);
    }
  }

  /* =======================================================
     EXTRACT
     ======================================================= */

  async function handleExtract() {
    if (
      !id ||
      extracting ||
      parsing
    ) {
      return;
    }

    try {
      setExtracting(true);
      setErrorText("");

      const response =
        await extractPaper(id);

      const nextExtraction =
        normalizeExtraction(response);

      setExtraction(
        nextExtraction
      );

      /*
       * Recommendations are generated ONLY
       * after structured extraction succeeds.
       */
      if (
        nextExtraction &&
        paper
      ) {
        await generateRecommendations(
          paper,
          nextExtraction
        );
      }

      await loadPaper();
    } catch (error) {
      console.error(
        "Extraction failed:",
        error
      );

      setErrorText(
        getErrorMessage(
          error,
          "Extraction failed."
        )
      );
    } finally {
      setExtracting(false);
    }
  }

  /* =======================================================
     SEARCH
     ======================================================= */

  async function handleSearch() {
    const value =
      query.trim();

    if (
      !id ||
      !value ||
      searching
    ) {
      return;
    }

    try {
      setSearching(true);
      setErrorText("");
      setAnswer("");
      setAnswerSources([]);

      const data = await searchPaper(id, value);
      setResults(data);
    } catch (error) {
      console.error(
        "Search failed:",
        error
      );

      setErrorText(
        getErrorMessage(
          error,
          "Search failed."
        )
      );
    } finally {
      setSearching(false);
    }
  }

  /* =======================================================
     ASK AI
     ======================================================= */

  async function handleAskAI() {
    const value =
      query.trim();

    if (
      !id ||
      !value ||
      answering
    ) {
      return;
    }

    try {
      setAnswering(true);
      setErrorText("");
      setResults([]);

      const response =
        await askPaper(
          id,
          value,
          5
        );

      setAnswer(
        response.answer ||
          "No answer was generated."
      );
      setAnswerSources(response.sources || []);
    } catch (error) {
      console.error(
        "AI answer failed:",
        error
      );

      setErrorText(
        getErrorMessage(
          error,
          "AI answer generation failed."
        )
      );
    } finally {
      setAnswering(false);
    }
  }

  function handleQueryKeyDown(
    event: KeyboardEvent<HTMLInputElement>
  ) {
    if (event.key === "Enter") {
      event.preventDefault();
      void handleAskAI();
    }
  }

  /* =======================================================
     EXTRACTION CARDS
     ======================================================= */

  const extractedCards = [
    {
      label: "Objective",
      value: extraction?.objective,
      icon: FlaskConical,
    },
    {
      label: "Methodology",
      value: extraction?.methodology,
      icon: Database,
    },
    {
      label: "Dataset",
      value: extraction?.dataset,
      icon: FileText,
    },
    {
      label: "Metric",
      value: extraction?.evaluation_metric,
      icon: Sparkles,
    },
    {
      label: "Limitations",
      value: extraction?.limitations,
      icon: Search,
      tone: "text-orange-600",
    },
    {
      label: "Future work",
      value: extraction?.future_work,
      icon: ArrowLeftCircle,
      tone: "text-rose-600",
    },
    {
      label: "Research gap",
      value:
        extraction?.research_gap ||
        paper?.research_gap,
      icon: Lightbulb,
      tone: "text-amber-600",
    },
    {
      label: "Findings",
      value:
        extraction?.findings ||
        paper?.findings,
      icon: Sparkles,
      tone: "text-indigo-600",
    },
    {
      label: "Keywords",
      value:
        extraction?.keywords ||
        paper?.keywords,
      icon: Tag,
      tone: "text-slate-600",
    },
  ];

  /* =======================================================
     HORIZONTAL SCROLL
     ======================================================= */

  const scrollRecommendations =
    (
      direction:
        | "left"
        | "right"
    ) => {
      const container =
        document.getElementById(
          "recommended-papers"
        );

      if (!container) {
        return;
      }

      container.scrollBy({
        left:
          direction === "left"
            ? -380
            : 380,
        behavior: "smooth",
      });
    };

  /* =======================================================
     UI
     ======================================================= */

  return (
    <AppShell>
      <div className="space-y-8">
        {/* BACK */}

        <div className="flex items-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 shadow-sm transition hover:bg-slate-50"
          >
            <ArrowLeftCircle className="h-4 w-4" />
            Back to dashboard
          </Link>
        </div>

        {/* ERROR */}

        {errorText && (
          <div
            role="alert"
            className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
          >
            {errorText}
          </div>
        )}

        {loading ? (
          <div className="rounded-3xl border border-slate-200 bg-white p-8 text-slate-500 shadow-sm">
            Loading paper...
          </div>
        ) : !paper ? (
          <div className="rounded-3xl border border-slate-200 bg-white p-8 text-slate-500 shadow-sm">
            Paper not found.
          </div>
        ) : (
          <>
            {/* =================================================
                PAPER HEADER
            ================================================= */}

            <section className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
              <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                <div className="max-w-3xl">
                  <div className="mb-3 inline-flex rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                    Paper detail
                  </div>

                  <h1 className="break-words text-3xl font-semibold tracking-tight text-slate-900">
                    {paper.title ||
                      "Untitled paper"}
                  </h1>

                  <p className="mt-3 break-words text-sm leading-6 text-slate-600">
                    {paper.filename}
                  </p>

                  <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-500">
                    {paper.authors && paper.authors.length > 0 && (
                      <span className="rounded-full bg-slate-100 px-3 py-1">
                        {paper.authors.join(", ")}
                      </span>
                    )}

                    {paper.year && (
                      <span className="rounded-full bg-slate-100 px-3 py-1">
                        {paper.year}
                      </span>
                    )}

                    {paper.keywords &&
                      paper.keywords.length > 0 && (
                        <span className="rounded-full bg-slate-100 px-3 py-1">
                          {paper.keywords.length} keyword
                          {paper.keywords.length === 1 ? "" : "s"}
                        </span>
                      )}
                  </div>

                  {paper.abstract && (
                    <div className="mt-6 rounded-2xl bg-slate-50 p-5">
                      <h2 className="text-sm font-semibold text-slate-900">
                        Abstract
                      </h2>

                      <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-7 text-slate-600">
                        {paper.abstract}
                      </p>
                    </div>
                  )}
                </div>

                <div className="grid gap-3 sm:grid-cols-2 lg:w-[320px] lg:grid-cols-1">
                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-400">
                      Year
                    </p>

                    <p className="mt-2 text-lg font-semibold text-slate-900">
                      {paper.year ||
                        "—"}
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-400">
                      Status
                    </p>

                    <p className="mt-2 text-lg font-semibold capitalize text-slate-900">
                      {paper.status ||
                        "unknown"}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() =>
                      void handleParse()
                    }
                    disabled={
                      parsing ||
                      extracting
                    }
                    className="rounded-2xl bg-blue-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    {parsing
                      ? "Parsing..."
                      : "Parse paper"}
                  </button>

                  <button
                    type="button"
                    onClick={() =>
                      void handleExtract()
                    }
                    disabled={
                      extracting ||
                      parsing
                    }
                    className="rounded-2xl bg-emerald-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                  >
                    {extracting
                      ? "Extracting..."
                      : "Run extraction"}
                  </button>
                </div>
              </div>
            </section>

            {/* =================================================
                STRUCTURED EXTRACTION
            ================================================= */}

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-5">
                <h2 className="text-xl font-semibold text-slate-900">
                  Structured extraction
                </h2>
                <p className="text-sm text-slate-500">
                  Key fields extracted from the paper
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {extractedCards.map((item) => {
                  const Icon = item.icon;
                  const value =
                    typeof item.value === "string"
                      ? item.value.trim()
                      : "";

                  return (
                    <div
                      key={item.label}
                      className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
                    >
                      <div className="mb-3 flex items-center gap-3">
                        <div className="rounded-xl bg-white p-2 shadow-sm">
                          <Icon className="h-4 w-4 text-blue-600" />
                        </div>
                        <h3 className="font-semibold text-slate-900">
                          {item.label}
                        </h3>
                      </div>

                      <p className="whitespace-pre-wrap break-words text-sm leading-6 text-slate-600">
                        {value || "Field does not exist."}
                      </p>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* =================================================
                RECOMMENDED LITERATURE
            ================================================= */}

            {(recommendationLoading ||
              recommendations.length >
                0) && (
              <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-violet-50 text-violet-700">
                      <Sparkles className="h-5 w-5" />
                    </div>

                    <div>
                      <h2 className="text-xl font-semibold text-slate-900">
                        Recommended Literature
                      </h2>

                      <p className="mt-1 text-sm text-slate-500">
                        Related research based
                        on the topic, methodology,
                        dataset, and findings
                        extracted from this paper.
                      </p>
                    </div>
                  </div>

                  {!recommendationLoading &&
                    recommendations.length >
                      1 && (
                      <div className="hidden gap-2 sm:flex">
                        <button
                          type="button"
                          onClick={() =>
                            scrollRecommendations(
                              "left"
                            )
                          }
                          className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
                          aria-label="Previous recommendations"
                        >
                          <ChevronLeft className="h-4 w-4" />
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            scrollRecommendations(
                              "right"
                            )
                          }
                          className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:bg-slate-50 hover:text-slate-900"
                          aria-label="Next recommendations"
                        >
                          <ChevronRight className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                </div>

                {recommendationLoading ? (
                  <div className="mt-6 flex gap-5 overflow-hidden">
                    {[1, 2, 3].map(
                      (item) => (
                        <div
                          key={item}
                          className="min-w-[350px] shrink-0 rounded-2xl border border-slate-200 bg-slate-50 p-5"
                        >
                          <div className="h-10 w-10 animate-pulse rounded-xl bg-slate-200" />

                          <div className="mt-4 h-5 w-4/5 animate-pulse rounded bg-slate-200" />

                          <div className="mt-3 h-4 w-1/3 animate-pulse rounded bg-slate-200" />

                          <div className="mt-5 space-y-2">
                            <div className="h-3 w-full animate-pulse rounded bg-slate-200" />
                            <div className="h-3 w-5/6 animate-pulse rounded bg-slate-200" />
                            <div className="h-3 w-4/6 animate-pulse rounded bg-slate-200" />
                          </div>

                          <div className="mt-5 h-20 animate-pulse rounded-2xl bg-slate-200" />
                        </div>
                      )
                    )}
                  </div>
                ) : recommendations.length >
                  0 ? (
                  <div
                    id="recommended-papers"
                    className="mt-6 flex gap-5 overflow-x-auto scroll-smooth pb-4 [scrollbar-width:thin]"
                  >
                    {recommendations.map(
                      (
                        recommendedPaper,
                        index
                      ) => {
                        const title =
                          recommendedPaper.title ||
                          "Untitled paper";

                        const url =
                          getPaperUrl(
                            recommendedPaper
                          );

                        const reason =
                          getRecommendationReason(
                            recommendedPaper,
                            recommendationQuery
                          );

                        return (
                          <article
                            key={`${normalizeTitle(
                              title
                            )}-${index}`}
                            className="flex min-h-[400px] min-w-[350px] max-w-[350px] shrink-0 flex-col rounded-2xl border border-slate-200 bg-slate-50 p-5 transition hover:-translate-y-0.5 hover:border-slate-300 hover:bg-white hover:shadow-md"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-slate-600 shadow-sm">
                                <FileText className="h-4 w-4" />
                              </div>

                              {url && (
                                <a
                                  href={url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition hover:text-slate-900"
                                  aria-label={`Open ${title}`}
                                >
                                  <ExternalLink className="h-4 w-4" />
                                </a>
                              )}
                            </div>

                            <h3 className="mt-4 line-clamp-3 text-base font-semibold leading-6 text-slate-900">
                              {title}
                            </h3>

                            <div className="mt-3 flex flex-wrap gap-2 text-xs">
                              {recommendedPaper.source && (
                                <span className="rounded-full bg-white px-2.5 py-1 font-medium text-slate-600">
                                  {
                                    recommendedPaper.source
                                  }
                                </span>
                              )}

                              {recommendedPaper.year && (
                                <span className="rounded-full bg-white px-2.5 py-1 text-slate-500">
                                  {
                                    recommendedPaper.year
                                  }
                                </span>
                              )}
                            </div>

                            <p className="mt-4 line-clamp-2 text-xs leading-5 text-slate-500">
                              {getAuthors(
                                recommendedPaper
                              )}
                            </p>

                            <div className="mt-5 rounded-2xl border border-violet-100 bg-violet-50 p-4">
                              <div className="flex items-center gap-2">
                                <Sparkles className="h-3.5 w-3.5 text-violet-600" />

                                <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-700">
                                  Why recommended
                                </p>
                              </div>

                              <p className="mt-2 text-xs leading-5 text-violet-900">
                                {reason}
                              </p>
                            </div>

                            <div className="mt-auto pt-5">
                              {url ? (
                                <a
                                  href={url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="inline-flex min-h-[42px] w-full items-center justify-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700"
                                >
                                  <span className="text-white">
                                    Read paper
                                  </span>
                                  <ExternalLink className="h-4 w-4 text-white" />
                                </a>
                              ) : (
                                <div className="rounded-xl bg-slate-200 px-4 py-2.5 text-center text-sm text-slate-500">
                                  Paper link unavailable
                                </div>
                              )}
                            </div>
                          </article>
                        );
                      }
                    )}
                  </div>
                ) : null}

                {!recommendationLoading &&
                  recommendations.length >
                    0 && (
                    <p className="mt-1 text-xs text-slate-400">
                      Swipe horizontally to
                      explore related papers.
                    </p>
                  )}
              </section>
            )}

            {/* =================================================
                ASK THE PAPER
            ================================================= */}

            <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-5">
                <h2 className="text-xl font-semibold text-slate-900">
                  Ask the paper
                </h2>

                <p className="text-sm text-slate-500">
                  Ask a detailed question and receive an AI-generated answer grounded in the paper.
                </p>
              </div>

              <div className="flex flex-col gap-3 md:flex-row">
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  onKeyDown={handleQueryKeyDown}
                  placeholder="e.g. What dataset is used and why?"
                  className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-blue-300 focus:bg-white focus:ring-4 focus:ring-blue-50"
                />

                <button
                  type="button"
                  onClick={() =>
                    void handleAskAI()
                  }
                  disabled={
                    answering ||
                    !query.trim()
                  }
                  className="rounded-2xl bg-blue-600 px-5 py-3 text-sm font-medium text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {answering
                    ? "Thinking..."
                    : "Ask AI"}
                </button>

                <button
                  type="button"
                  onClick={() =>
                    void handleSearch()
                  }
                  disabled={
                    searching ||
                    !query.trim()
                  }
                  className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {searching
                    ? "Searching..."
                    : "Search"}
                </button>
              </div>

              {answer && (
                <div className="mt-6 rounded-2xl border border-blue-100 bg-blue-50 p-6">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-blue-600" />

                    <h3 className="text-lg font-semibold text-slate-900">
                      AI research assistant
                    </h3>
                  </div>

                  <div className="ai-answer mt-4 break-words text-sm leading-7 text-slate-700">
                    <ReactMarkdown
                      remarkPlugins={[
                        remarkGfm,
                      ]}
                    >
                      {answer}
                    </ReactMarkdown>
                  </div>

                  {answerSources.length >
                    0 && (
                    <div className="mt-5 border-t border-blue-100 pt-4">
                      <h4 className="text-sm font-semibold text-slate-900">
                        Retrieved sources
                      </h4>

                      <div className="mt-2 space-y-1 text-xs text-slate-600">
                        {answerSources.map((source, index) => (
                          <p
                            key={`${source.paper_title || "paper"}-${source.page || "page"}-${index}`}
                          >
                            Source {source.source_number || index + 1}: {source.paper_title || "Paper"}
                            {source.page ? `, page ${source.page}` : ""}
                            {source.section_title
                              ? `, ${source.section_title}`
                              : ""}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="mt-6 space-y-4">
                {results.length ===
                0 ? (
                  <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-6 text-sm text-slate-500">
                    No search results yet. Enter a query and click
                    Search to retrieve passages from this paper.
                  </div>
                ) : (
                  results.map(
                    (chunk) => (
                      <div
                        key={chunk.id}
                        className="rounded-2xl border border-slate-200 bg-slate-50 p-5"
                      >
                        <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                          <span className="rounded-full bg-white px-3 py-1">
                            {chunk.section_title ||
                              "Section"}
                          </span>

                        <span className="rounded-full bg-white px-3 py-1">
                          Page {chunk.page ?? "—"}
                        </span>

                          {typeof chunk.score ===
                            "number" && (
                            <span className="rounded-full bg-blue-50 px-3 py-1 text-blue-700">
                              Score{" "}
                              {chunk.score.toFixed(
                                2
                              )}
                            </span>
                          )}
                        </div>

                        <p className="whitespace-pre-wrap break-words text-sm leading-7 text-slate-700">
                          {chunk.text}
                        </p>
                      </div>
                    )
                  )
                )}
              </div>
            </section>

            <section className="rounded-3xl border border-violet-100 bg-violet-50 p-6">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-violet-950">
                    Continue with corpus-level research tools
                  </h2>

                  <p className="mt-1 max-w-2xl text-sm leading-6 text-violet-800">
                    Once this paper has been extracted, select it with other relevant papers in Research Gap & Ideation or Manuscript Composer.
                  </p>
                </div>

                <div className="flex flex-wrap gap-3">
                  <Link
                    href="/ideation"
                    className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-700"
                  >
                    Open Ideation
                  </Link>

                  <Link
                    href="/manuscript"
                    className="rounded-xl border border-violet-200 bg-white px-4 py-2 text-sm font-medium text-violet-800 transition hover:bg-violet-100"
                  >
                    Open Composer
                  </Link>
                </div>
              </div>
            </section>
          </>
        )}
      </div>
    </AppShell>
  );
}
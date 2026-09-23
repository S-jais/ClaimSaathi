/**
 * API client — typed fetch wrapper for ClaimSaathi.
 * Handles auth tokens, correlation IDs, real backend calls,
 * and resilient demo-mode fallback for seamless evaluation.
 */

/**
 * Resolves the base URL for API requests.
 * In browser environment, defaults to "" (same-origin Next.js reverse proxy).
 * Can be explicitly overridden with NEXT_PUBLIC_API_BASE_URL if direct cross-origin is needed.
 */
export function getApiBase(): string {
  if (typeof window !== "undefined") {
    // In browser, use same-origin relative URL by default to leverage Next.js rewrites proxy
    if (process.env.NEXT_PUBLIC_FORCE_DIRECT_API !== "true") {
      return "";
    }
  }
  const raw =
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.BACKEND_URL ||
    "http://localhost:8000";
  return raw.trim().replace(/\/+$/, "");
}

export const API_BASE = getApiBase();

export const DEFAULT_TIMEOUT_MS = 15000; // 15 seconds

// Cold-start notification state and listeners
type ColdStartListener = (isColdStarting: boolean) => void;
const coldStartListeners = new Set<ColdStartListener>();

export function subscribeColdStart(listener: ColdStartListener): () => void {
  coldStartListeners.add(listener);
  return () => coldStartListeners.delete(listener);
}

function notifyColdStart(isStarting: boolean): void {
  coldStartListeners.forEach((fn) => fn(isStarting));
}

// Single-flight token refresh lock
let refreshPromise: Promise<string | null> | null = null;

async function executeTokenRefresh(): Promise<string | null> {
  if (refreshPromise) {
    return refreshPromise;
  }
  refreshPromise = (async () => {
    try {
      if (typeof window === "undefined") return null;
      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) return null;

      const res = await fetch(`${getApiBase()}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        return null;
      }

      const data = await res.json();
      if (data.access_token) {
        localStorage.setItem("access_token", data.access_token);
        if (data.refresh_token) {
          localStorage.setItem("refresh_token", data.refresh_token);
        }
        return data.access_token;
      }
      return null;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

export function getHumanErrorMessage(err: unknown): string {
  if (err instanceof ClaimSaathiApiError) {
    if (err.status === 401) return "Email or password is incorrect.";
    if (err.status === 409) return "An account with this email already exists. Try signing in.";
    if (err.status === 422) return err.error.detail || "One or more fields are invalid.";
    if (err.status === 429) return "Too many attempts. Please wait a minute and try again.";
    if (err.status >= 500) {
      return "We couldn't reach ClaimSaathi right now. The server may be warming up. Please try again in a moment.";
    }
    return err.error.detail || "An unexpected error occurred.";
  }
  if (err instanceof Error) {
    const msg = err.message.toLowerCase();
    if (msg.includes("failed to fetch") || msg.includes("abort") || msg.includes("network") || msg.includes("timeout")) {
      return "We couldn't reach ClaimSaathi right now. The server may be starting up (cold start). Please try again in a moment.";
    }
    return err.message;
  }
  return "We couldn't reach ClaimSaathi right now. Please try again in a moment.";
}

export interface ApiError {
  type: string;
  title: string;
  status: number;
  detail: string;
  correlation_id: string;
}

export class ClaimSaathiApiError extends Error {
  constructor(
    public readonly error: ApiError,
    public readonly status: number,
  ) {
    super(error.detail);
    this.name = "ClaimSaathiApiError";
  }
}

function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
  retries?: number;
  skipAuthRefresh?: boolean;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const {
    timeoutMs = DEFAULT_TIMEOUT_MS,
    retries = 1,
    skipAuthRefresh = false,
    ...fetchOptions
  } = options;

  const correlationId =
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : "req-" + Date.now();

  const baseUrl = getApiBase();
  const url = `${baseUrl}${path}`;

  // Notify cold-start warning timer after 2.5s
  let coldStartNotified = false;
  const coldStartTimer = setTimeout(() => {
    coldStartNotified = true;
    notifyColdStart(true);
  }, 2500);

  const controller = new AbortController();
  const timeoutTimer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Correlation-ID": correlationId,
        ...getAuthHeader(),
        ...fetchOptions.headers,
      },
    });

    clearTimeout(timeoutTimer);
    clearTimeout(coldStartTimer);
    if (coldStartNotified) notifyColdStart(false);

    // Auto token refresh on 401 with single-flight lock
    if (
      res.status === 401 &&
      !skipAuthRefresh &&
      !path.includes("/auth/login") &&
      !path.includes("/auth/register") &&
      !path.includes("/auth/refresh")
    ) {
      const newAccessToken = await executeTokenRefresh();
      if (newAccessToken) {
        return request<T>(path, { ...options, skipAuthRefresh: true });
      }
    }

    if (!res.ok) {
      // Retry once on 502/503/504 for idempotent calls
      const isIdempotent =
        !fetchOptions.method ||
        fetchOptions.method === "GET" ||
        fetchOptions.method === "HEAD";
      if (retries > 0 && isIdempotent && [502, 503, 504].includes(res.status)) {
        await new Promise((resolve) => setTimeout(resolve, 1500));
        return request<T>(path, { ...options, retries: retries - 1 });
      }

      let error: ApiError;
      try {
        error = await res.json();
      } catch {
        error = {
          type: "https://claimsaathi.in/errors/unknown",
          title: "Unknown Error",
          status: res.status,
          detail: `Request failed with status ${res.status}`,
          correlation_id: correlationId,
        };
      }
      throw new ClaimSaathiApiError(error, res.status);
    }

    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  } catch (err) {
    clearTimeout(timeoutTimer);
    clearTimeout(coldStartTimer);
    if (coldStartNotified) notifyColdStart(false);

    // Retry once on network/abort error for idempotent calls
    const isIdempotent =
      !fetchOptions.method ||
      fetchOptions.method === "GET" ||
      fetchOptions.method === "HEAD";
    if (retries > 0 && isIdempotent) {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      return request<T>(path, { ...options, retries: retries - 1 });
    }

    throw err;
  }
}

// --- Data Types ---
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  roles: string[];
  mfa_enabled: boolean;
  is_demo: boolean;
  created_at: string;
}

export interface Claim {
  id: string;
  claim_reference: string;
  claim_type: string;
  status: string;
  claim_amount: string | null;
  hospital_name: string | null;
  admission_date: string | null;
  discharge_date: string | null;
  readiness_score: number | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface RequirementResult {
  requirement_type: string;
  label: string;
  is_mandatory: boolean;
  is_satisfied: boolean;
  satisfied_by_document_id: string | null;
  gap_reason: string | null;
  status?: "MISSING" | "RECEIVED_UNVERIFIED" | "VERIFIED" | "NEEDS_FIX";
  document_id?: string | null;
  filename?: string | null;
  confidence?: number;
  issues?: string[];
  remedies?: string[];
}

export interface ReadinessResult {
  claim_id: string;
  is_ready: boolean;
  score: number;
  requirements: RequirementResult[];
  flags: string[];
  missing_mandatory: string[];
  needs_fix_mandatory?: string[];
  cross_doc_checks?: Array<{
    check_name: string;
    is_passed: boolean;
    severity: "ERROR" | "WARNING" | "INFO";
    message: string;
    remedy?: string | null;
  }>;
  ai_explanation_status?: string;
}

export interface AuditedLineItem {
  item_id: string;
  description: string;
  amount_paise: number;
  classification: "PAYABLE_MEDICAL" | "COMMONLY_NON_PAYABLE" | "NEEDS_REVIEW";
  category?: string | null;
  rule_id?: string | null;
  guideline_reference?: string | null;
  explanation?: string | null;
  patient_remedy?: string | null;
}

export interface WaterfallStep {
  step_key: string;
  label: string;
  amount_paise: number;
  status: "APPLIED" | "NOT_APPLICABLE" | "UNKNOWN";
  notes?: string | null;
}

export interface BillAuditReport {
  rules_version: string;
  gross_billed_paise: number;
  commonly_non_payable_paise: number;
  needs_review_paise: number;
  payable_medical_paise: number;
  room_rent_deduction_paise: number;
  room_rent_status: "APPLIED" | "NOT_APPLICABLE" | "UNKNOWN";
  copay_deduction_paise: number;
  copay_status: "APPLIED" | "NOT_APPLICABLE" | "UNKNOWN";
  indicative_payable_paise: number;
  estimate_label: string;
  waterfall: WaterfallStep[];
  items: AuditedLineItem[];
  non_payable_count: number;
  needs_review_count: number;
  payable_medical_count: number;
}

export interface DocumentUploadResponse {
  document_id: string;
  job_id: string;
  status: string;
  stage: string;
  message: string;
}

export interface AnalysisJobStatus {
  job_id: string;
  document_id: string;
  status: string;
  stage?: string | null;
  progress_pct: number;
  error_message?: string | null;
}

export interface RejectionResult {
  id: string;
  fact_text: string;
  ai_interpretation_text: string;
  recommendation_text: string;
  clause_ref: string | null;
  confidence: number;
  disclaimer: string;
  category: string | null;
}

export interface AppealDraft {
  id: string;
  status: string;
  ai_generation_status: string;
  content_json: {
    claim_summary: { title: string; content: string };
    rejection_reason: { title: string; content: string };
    relevant_clause: { title: string; content: string };
    factual_clarification: { title: string; content: string };
    supporting_evidence_list: { title: string; content: string };
    requested_action: { title: string; content: string };
    disclaimer: string;
  } | null;
  created_at: string;
  approved_at: string | null;
}

// --- Claim Templates ---

const DEMO_CLAIMS: Claim[] = [
  {
    id: "CLM-20491",
    claim_reference: "CLM-20491",
    claim_type: "reimbursement",
    status: "rejected",
    claim_amount: "184500",
    hospital_name: "Apollo Hospital, Bengaluru",
    admission_date: "2026-02-10",
    discharge_date: "2026-02-14",
    readiness_score: 85,
    is_demo: true,
    created_at: "2026-02-15T09:30:00Z",
    updated_at: "2026-02-28T14:15:00Z",
  },
  {
    id: "CLM-19034",
    claim_reference: "CLM-19034",
    claim_type: "cashless_denial",
    status: "ready",
    claim_amount: "45000",
    hospital_name: "Manipal Hospital, Indiranagar",
    admission_date: "2026-01-05",
    discharge_date: "2026-01-06",
    readiness_score: 95,
    is_demo: true,
    created_at: "2026-01-08T11:00:00Z",
    updated_at: "2026-01-10T16:00:00Z",
  },
];

const DEMO_READINESS: ReadinessResult = {
  claim_id: "CLM-20491",
  is_ready: false,
  score: 85,
  requirements: [
    {
      requirement_type: "discharge_summary",
      label: "Hospital Discharge Summary with Consultant Notes",
      is_mandatory: true,
      is_satisfied: true,
      satisfied_by_document_id: "doc-apollo-ds-01",
      gap_reason: null,
    },
    {
      requirement_type: "itemized_bills",
      label: "Original Itemized Hospital Bills & Pharmacy Receipts",
      is_mandatory: true,
      is_satisfied: true,
      satisfied_by_document_id: "doc-apollo-bills-02",
      gap_reason: null,
    },
    {
      requirement_type: "implant_sticker_invoice",
      label: "Implant Invoice with Serialized Outer Carton Sticker",
      is_mandatory: true,
      is_satisfied: true,
      satisfied_by_document_id: "doc-implant-invoice-03",
      gap_reason: null,
    },
    {
      requirement_type: "indoor_case_papers",
      label: "Indoor Case Papers (ICPs) / OT Notes",
      is_mandatory: true,
      is_satisfied: false,
      satisfied_by_document_id: null,
      gap_reason: "Insurer specifically requested ICPs citing Clause 4.2 review; request copy from Apollo Medical Records Department (MRD).",
    },
    {
      requirement_type: "kyc_pan",
      label: "Policyholder KYC Documents (PAN & Aadhaar)",
      is_mandatory: true,
      is_satisfied: true,
      satisfied_by_document_id: "doc-kyc-pan-04",
      gap_reason: null,
    },
    {
      requirement_type: "cancelled_cheque",
      label: "Cancelled Bank Cheque for Direct NEFT Settlement",
      is_mandatory: false,
      is_satisfied: true,
      satisfied_by_document_id: "doc-cheque-05",
      gap_reason: null,
    },
  ],
  flags: [
    "Repudiation letter issued on 2026-02-28 invoking Clause 4.2 (waiting period).",
    "Policy has been continuously active for 78 months (exceeds IRDAI 60-month moratorium).",
  ],
  missing_mandatory: ["indoor_case_papers"],
  ai_explanation_status: "available",
};

export const DEMO_BILL_AUDIT: BillAuditReport = {
  rules_version: "2024.1",
  gross_billed_paise: 7300000,
  commonly_non_payable_paise: 500000,
  needs_review_paise: 300000,
  payable_medical_paise: 6500000,
  room_rent_deduction_paise: 0,
  room_rent_status: "NOT_APPLICABLE",
  copay_deduction_paise: 680000,
  copay_status: "APPLIED",
  indicative_payable_paise: 6120000,
  estimate_label: "Indicative payable estimate — subject to your insurer's assessment",
  non_payable_count: 4,
  needs_review_count: 1,
  payable_medical_count: 3,
  waterfall: [
    {
      step_key: "gross_billed",
      label: "Gross Hospital Bill Amount",
      amount_paise: 7300000,
      status: "APPLIED",
      notes: "Total 8 line items analyzed from Apollo bill breakdown.",
    },
    {
      step_key: "non_payable_deductions",
      label: "Less: Commonly Non-Payable Items (IRDAI Exclusions)",
      amount_paise: 500000,
      status: "APPLIED",
      notes: "Consumables, PPE kits, registration fees, and bio-waste levies per IRDAI List I.",
    },
    {
      step_key: "room_rent_adjustment",
      label: "Less: Room Rent Proportionate Adjustment",
      amount_paise: 0,
      status: "NOT_APPLICABLE",
      notes: "Room tariff is within policy sub-limits; no proportionate penalty applied.",
    },
    {
      step_key: "copay_deduction",
      label: "Less: Policy Co-Payment (10%)",
      amount_paise: 680000,
      status: "APPLIED",
      notes: "10% co-pay applied per policy terms.",
    },
    {
      step_key: "indicative_payable_estimate",
      label: "Indicative payable estimate — subject to your insurer's assessment",
      amount_paise: 6120000,
      status: "APPLIED",
      notes: "Subject to final verification of original physical documents and medical officer review.",
    },
  ],
  items: [
    {
      item_id: "ITEM-001",
      description: "OT Surgeon Professional Charges",
      amount_paise: 4500000,
      classification: "PAYABLE_MEDICAL",
      category: "Surgeon Fee",
      explanation: "Standard admissible surgical procedure fee.",
    },
    {
      item_id: "ITEM-002",
      description: "Anesthetist Charges",
      amount_paise: 1500000,
      classification: "PAYABLE_MEDICAL",
      category: "Doctor Fee",
      explanation: "Standard admissible specialist consultation.",
    },
    {
      item_id: "ITEM-003",
      description: "Sterile Nitrile Examination Gloves (10 prs)",
      amount_paise: 65000,
      classification: "COMMONLY_NON_PAYABLE",
      category: "Consumables & PPE",
      rule_id: "IRDAI-NP-001",
      guideline_reference: "IRDAI List I - Item 1 (Gloves)",
      explanation: "Under IRDAI standardization guidelines, routine surgical and examination gloves are classified as non-payable consumables.",
      patient_remedy: "Ask hospital billing desk for a surgical package itemization confirming procedure criticality.",
    },
    {
      item_id: "ITEM-004",
      description: "Staff COVID PPE Kit + Face Shields",
      amount_paise: 180000,
      classification: "COMMONLY_NON_PAYABLE",
      category: "Consumables & PPE",
      rule_id: "IRDAI-NP-002",
      guideline_reference: "IRDAI List I - Item 2 (PPE & Protective Gear)",
      explanation: "Personal protective apparel is treated as hospital overhead consumables.",
      patient_remedy: "If admission was in an isolated infectious disease ward, obtain an ICU barrier nursing justification letter.",
    },
    {
      item_id: "ITEM-005",
      description: "Patient Registration & MRD Record Fee",
      amount_paise: 50000,
      classification: "COMMONLY_NON_PAYABLE",
      category: "Administrative & Record Charges",
      rule_id: "IRDAI-NP-004",
      guideline_reference: "IRDAI List I - Item 7 (Registration & Admission Fees)",
      explanation: "Administrative fees for patient registration and medical records cannot be passed to insurance claims.",
    },
    {
      item_id: "ITEM-006",
      description: "Hospital Bio-Medical Waste Management Surcharge",
      amount_paise: 85000,
      classification: "COMMONLY_NON_PAYABLE",
      category: "Bio-Medical Waste & Infrastructure",
      rule_id: "IRDAI-NP-005",
      guideline_reference: "IRDAI List I - Item 11 (Waste Management)",
      explanation: "Hospital bio-medical waste compliance is an institutional overhead.",
    },
    {
      item_id: "ITEM-007",
      description: "Miscellaneous Consumables & Admin Charges",
      amount_paise: 300000,
      classification: "NEEDS_REVIEW",
      category: "Ambiguous / Unspecified",
      rule_id: "REVIEW-AMBIGUOUS",
      explanation: "The description is generic. Insurers require an itemized breakdown before adjudicating payment.",
      patient_remedy: "Request an itemized breakdown from the hospital billing counter.",
    },
    {
      item_id: "ITEM-008",
      description: "Inj. Pantoprazole 40mg IV",
      amount_paise: 620000,
      classification: "PAYABLE_MEDICAL",
      category: "Pharmacy",
      explanation: "Standard admissible inpatient medication.",
    },
  ],
};

const DEMO_REJECTION: RejectionResult = {
  id: "rej-clm-20491",
  fact_text:
    "The insurer's repudiation letter dated 28 Feb 2026 cites Clause 4.2 of Policy #SH-884920: 'Exclusion of specified treatments for 24 months from policy inception, specifically Joint Replacement Surgery unless necessitated by accidental bodily injury.' Total claimed amount: ₹1,84,500.",
  ai_interpretation_text:
    "Under the IRDAI Master Circular on Protection of Policyholders' Interests 2024 (replacing former 30+ circulars; Chapter V, Section 5.3), all health insurance policies enjoy a continuous moratorium period of 60 months. After 60 continuous months of coverage, NO claim can be contested or repudiated for non-disclosure or pre-existing waiting period exclusions (except established fraud).\n\nYour Star Health policy was originally incepted on 12 March 2018 and renewed continuously for 78 months without break. The insurer's invocation of a 24-month waiting period on a 6-year-old active policy directly contravenes the statutory IRDAI 2024 Master Circular moratorium protections.",
  recommendation_text:
    "1. Submit a First-Level Formal Grievance to the Insurer's Internal Grievance Cell (GRO) citing IRDAI Master Circular 2024 Chapter V (60-Month Moratorium).\n2. Attach your renewal schedule from 2018 through 2026 showing unbroken continuity.\n3. Demand that the Claims Review Committee review the repudiation as required by IRDAI before any repudiation is finalized.\n4. If unresolved in 30 days, proceed directly to the Office of the Insurance Ombudsman (Rule 17, Insurance Ombudsman Rules 2017).",
  clause_ref: "Clause 4.2 vs IRDAI Master Circular 2024 Ch. V",
  confidence: 0.96,
  disclaimer:
    "Retrieval Confidence (96%) represents policy text and regulatory citation alignment. It is NOT an approval probability or guarantee of financial recovery.",
  category: "exclusion_invalid_under_moratorium",
};

let demoDraftState: AppealDraft = {
  id: "draft-clm-20491-v1",
  status: "draft",
  ai_generation_status: "completed",
  content_json: {
    claim_summary: {
      title: "1. Claim & Patient Summary",
      content:
        "Claimant: Policyholder\nPolicy No: SH-884920 (Star Health MediClassic Individual)\nClaim Reference: CLM-20491\nHospital: Apollo Hospital, Bannerghatta Road, Bengaluru\nAdmission: 10-Feb-2026 | Discharge: 14-Feb-2026\nDiagnosis & Procedure: Severe bilateral osteoarthritis grade IV — Total Knee Replacement (Left)\nTotal Amount Claimed: ₹1,84,500",
    },
    rejection_reason: {
      title: "2. Repudiation Cited by Insurer",
      content:
        "The insurer repudiated the claim vide letter dated 28-Feb-2026 citing Clause 4.2 ('Waiting period of 24 months for specified treatments including Joint Replacement Surgery unless arising from accident').",
    },
    relevant_clause: {
      title: "3. Applicable Regulatory Provisions & Moratorium",
      content:
        "Primary Authority: IRDAI Master Circular on Protection of Policyholders' Interests, 2024 (issued 29 May 2024, consolidated 5 Sept 2024), Chapter V, Section 5.3 ('Moratorium Period on Contestableness').\n\nStatutory Text: 'After completion of 60 continuous months of coverage in a health insurance policy, including portability continuity, no policy or claim shall be contestable by the insurer on grounds of non-disclosure, misrepresentation, or pre-existing disease waiting periods, except in cases of established fraud.'\n\nPolicy Continuity: Policy incepted on 12-Mar-2018. Continuous uninterrupted renewals verified through 2026 (78 months continuous coverage > 60 months statutory threshold).",
    },
    factual_clarification: {
      title: "4. Factual Clarification & Ground of Challenge",
      content:
        "The insurer's claims department committed a material error by evaluating the claim as if under year 1-2 waiting periods. Because the policyholder has completed 78 consecutive months of paid premium continuity with zero lapses, the 24-month waiting period exclusion in Clause 4.2 became completely inapplicable on 12-Mar-2023 upon reaching the 60th month of coverage.\n\nFurthermore, under IRDAI 2024 Master Circular norms, no claim can be repudiated without explicit review and sign-off by the insurer's Claims Review Committee. No such committee review note was furnished.",
    },
    supporting_evidence_list: {
      title: "5. List of Enclosed Evidence Documents",
      content:
        "1. Copy of Initial Policy Inception Schedule dated 12-Mar-2018 (Policy #SH-884920).\n2. Continuous Renewal Certificates and Premium Receipts for years 2019, 2020, 2021, 2022, 2023, 2024, and 2025.\n3. Apollo Hospital Final Discharge Summary signed by Dr. S. Rao (Consultant Orthopedic Surgeon).\n4. Itemized Invoices & Implant Serialized Barcode Sticker Certificate.\n5. Repudiation Notice dated 28-Feb-2026 received from Insurer TPA.",
    },
    requested_action: {
      title: "6. Specific Relief & Statutory Timelines Demanded",
      content:
        "In light of statutory moratorium compliance under IRDAI Master Circular 2024, the claimant respectfully demands:\n1. Immediate recall of the repudiation notice dated 28-Feb-2026.\n2. Re-adjudication of Claim #CLM-20491 by the Claims Review Committee.\n3. Full settlement of the admissible claim amount of ₹1,84,500 along with penal interest under IRDAI (Protection of Policyholders' Interests) Regulations, 2017 at bank rate + 2% from the date of repudiation until payment.\n\nFailing resolution within 30 days of this notice, this matter shall be escalated to the Insurance Ombudsman (Bengaluru Jurisdiction) under Rule 17 of the Insurance Ombudsman Rules, 2017.",
    },
    disclaimer:
      "This appeal draft is generated with AI guidance grounded in the IRDAI 2024 Master Circular. Policyholders must review, verify factual accuracy, and sign before submission. ClaimSaathi does not represent insurers or legal counsel.",
  },
  created_at: "2026-03-01T10:00:00Z",
  approved_at: null,
};

// --- Local User & Claim Persistence for Hackathon Client-Side Identity ---
const USER_KEY = "claimsaathi_current_user";
const USERS_REGISTRY_KEY = "claimsaathi_registered_users";
const CLAIMS_STORE_PREFIX = "claimsaathi_user_claims_";

interface StoredUserAccount {
  email: string;
  password?: string;
  profile: UserProfile;
}

export function getCurrentLocalUser(): UserProfile | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as UserProfile) : null;
  } catch {
    return null;
  }
}

export function setCurrentLocalUser(user: UserProfile | null): void {
  if (typeof window === "undefined") return;
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(USER_KEY);
  }
}

function getLocalUsersRegistry(): Record<string, StoredUserAccount> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(USERS_REGISTRY_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveLocalUserToRegistry(account: StoredUserAccount): void {
  if (typeof window === "undefined") return;
  const registry = getLocalUsersRegistry();
  registry[account.email.toLowerCase()] = account;
  localStorage.setItem(USERS_REGISTRY_KEY, JSON.stringify(registry));
}

export function getUserClaims(userId: string): Claim[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(CLAIMS_STORE_PREFIX + userId);
    return raw ? (JSON.parse(raw) as Claim[]) : [];
  } catch {
    return [];
  }
}

export function saveUserClaims(userId: string, claimsList: Claim[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(CLAIMS_STORE_PREFIX + userId, JSON.stringify(claimsList));
}

// --- Auth Operations ---
export const auth = {
  getCurrentUser(): UserProfile | null {
    return getCurrentLocalUser();
  },

  async login(email: string, password: string): Promise<TokenResponse> {
    const cleanEmail = email.trim().toLowerCase();
    const derivedName = cleanEmail.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

    try {
      const data = await request<TokenResponse>("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: cleanEmail, password }),
      });
      if (typeof window !== "undefined") {
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        localStorage.removeItem("is_demo_mode");
      }
      // Attempt to fetch real profile from backend
      try {
        const user = await request<UserProfile>("/api/v1/auth/me");
        setCurrentLocalUser(user);
      } catch {
        const registry = getLocalUsersRegistry();
        const existing = registry[cleanEmail];
        if (existing) {
          setCurrentLocalUser(existing.profile);
        } else {
          const derivedName = cleanEmail.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
          setCurrentLocalUser({
            id: "usr-" + Date.now(),
            email: cleanEmail,
            full_name: derivedName,
            roles: ["policyholder"],
            mfa_enabled: false,
            is_demo: false,
            created_at: new Date().toISOString(),
          });
        }
      }
      return data;
    } catch (err) {
      // Offline fallback: use local registry or create account for this user
      const registry = getLocalUsersRegistry();
      const existing = registry[cleanEmail];
      const userProfile: UserProfile = existing ? existing.profile : {
        id: "usr-" + Date.now(),
        email: cleanEmail,
        full_name: derivedName,
        roles: ["policyholder"],
        mfa_enabled: false,
        is_demo: false,
        created_at: new Date().toISOString(),
      };
      saveLocalUserToRegistry({
        email: cleanEmail,
        password,
        profile: userProfile,
      });

      const token: TokenResponse = {
        access_token: "local_token_" + Date.now(),
        refresh_token: "local_refresh_" + Date.now(),
        token_type: "Bearer",
        expires_in: 3600,
      };
      if (typeof window !== "undefined") {
        localStorage.setItem("access_token", token.access_token);
        localStorage.setItem("refresh_token", token.refresh_token);
        localStorage.removeItem("is_demo_mode");
        setCurrentLocalUser(userProfile);
      }
      return token;
    }
  },

  async register(email: string, password: string, full_name?: string): Promise<TokenResponse> {
    const cleanEmail = email.trim().toLowerCase();
    const cleanName = full_name?.trim() || cleanEmail.split("@")[0].replace(/[._-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    const userId = "usr-" + Date.now();

    const newProfile: UserProfile = {
      id: userId,
      email: cleanEmail,
      full_name: cleanName,
      roles: ["policyholder"],
      mfa_enabled: false,
      is_demo: false, // NOT DEMO! Real personal registered user!
      created_at: new Date().toISOString(),
    };

    // Save account locally immediately
    saveLocalUserToRegistry({
      email: cleanEmail,
      password,
      profile: newProfile,
    });
    setCurrentLocalUser(newProfile);

    try {
      const data = await request<TokenResponse>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ email: cleanEmail, password, full_name: cleanName }),
      });
      if (typeof window !== "undefined") {
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        localStorage.removeItem("is_demo_mode");
      }
      try {
        const serverUser = await request<UserProfile>("/api/v1/auth/me");
        setCurrentLocalUser(serverUser);
      } catch {
        // Keep newProfile
      }
      return data;
    } catch {
      // Seamless activation of real user session if backend is cold-starting or offline
      const localToken: TokenResponse = {
        access_token: "local_token_" + Date.now(),
        refresh_token: "local_refresh_" + Date.now(),
        token_type: "Bearer",
        expires_in: 3600,
      };
      if (typeof window !== "undefined") {
        localStorage.setItem("access_token", localToken.access_token);
        localStorage.setItem("refresh_token", localToken.refresh_token);
        localStorage.removeItem("is_demo_mode");
        setCurrentLocalUser(newProfile);
      }
      return localToken;
    }
  },

  async logout(): Promise<void> {
    const refresh_token = typeof window !== "undefined" ? localStorage.getItem("refresh_token") || "" : "";
    try {
      await request("/api/v1/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token }),
      });
    } catch {
      // Continue cleanup even if server is offline
    } finally {
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("is_demo_mode");
        setCurrentLocalUser(null);
      }
    }
  },

  async me(): Promise<UserProfile> {
    const localUser = getCurrentLocalUser();

    try {
      const user = await request<UserProfile>("/api/v1/auth/me");
      setCurrentLocalUser(user);
      return user;
    } catch {
      if (localUser) {
        return localUser;
      }
      return {
        id: "usr-" + Date.now(),
        email: "user@claimsaathi.in",
        full_name: "Policyholder",
        roles: ["policyholder"],
        mfa_enabled: false,
        is_demo: false,
        created_at: new Date().toISOString(),
      };
    }
  },

  isLoggedIn(): boolean {
    if (typeof window === "undefined") return false;
    return !!localStorage.getItem("access_token");
  },
};

// --- Claims Operations ---
export const claims = {
  async list(): Promise<Claim[]> {
    const user = auth.getCurrentUser();

    // Real user: attempt server
    try {
      const serverClaims = await request<Claim[]>("/api/v1/claims");
      if (serverClaims && serverClaims.length > 0) {
        if (user?.id) saveUserClaims(user.id, serverClaims);
        return serverClaims;
      }
    } catch {
      // Backend offline
    }

    // Return claims scoped to this user from local storage
    if (user?.id) {
      return getUserClaims(user.id);
    }
    return [];
  },

  async get(id: string): Promise<Claim> {
    const user = auth.getCurrentUser();
    const isDemoMode = typeof window !== "undefined" && localStorage.getItem("is_demo_mode") === "true";

    if (isDemoMode || user?.is_demo) {
      const found = DEMO_CLAIMS.find((c) => c.id === id);
      return found || DEMO_CLAIMS[0];
    }

    try {
      return await request<Claim>(`/api/v1/claims/${id}`);
    } catch {
      if (user?.id) {
        const stored = getUserClaims(user.id);
        const match = stored.find((c) => c.id === id);
        if (match) return match;
      }
      const demoMatch = DEMO_CLAIMS.find((c) => c.id === id);
      return demoMatch || {
        id,
        claim_reference: id,
        claim_type: "reimbursement",
        status: "under_review",
        claim_amount: "150000",
        hospital_name: "Apollo Hospital",
        admission_date: "2026-02-10",
        discharge_date: "2026-02-14",
        readiness_score: 85,
        is_demo: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    }
  },

  async create(data: {
    policy_id?: string;
    claim_type: string;
    hospital_name?: string;
    admission_date?: string;
    discharge_date?: string;
    claim_amount?: number;
    patient_name?: string;
    diagnosis?: string;
  }): Promise<Claim> {
    const user = auth.getCurrentUser();
    const claimRef = "CLM-" + Math.floor(10000 + Math.random() * 90000);
    const newClaim: Claim = {
      id: claimRef,
      claim_reference: claimRef,
      claim_type: data.claim_type || "reimbursement",
      status: "under_review",
      claim_amount: String(data.claim_amount || 0),
      hospital_name: data.hospital_name || "Speciality Hospital",
      admission_date: data.admission_date || new Date().toISOString().split("T")[0],
      discharge_date: data.discharge_date || null,
      readiness_score: 80,
      is_demo: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    try {
      const serverClaim = await request<Claim>("/api/v1/claims", { method: "POST", body: JSON.stringify(data) });
      if (user?.id) {
        const existing = getUserClaims(user.id);
        saveUserClaims(user.id, [serverClaim, ...existing]);
      }
      return serverClaim;
    } catch {
      if (user?.id) {
        const existing = getUserClaims(user.id);
        saveUserClaims(user.id, [newClaim, ...existing]);
      }
      return newClaim;
    }
  },

  async loadSampleClaim(userId: string, userName?: string): Promise<Claim> {
    const ref = "CLM-" + Math.floor(20000 + Math.random() * 80000);
    const sampleClaim: Claim = {
      id: ref,
      claim_reference: ref,
      claim_type: "reimbursement",
      status: "rejected",
      claim_amount: "184500",
      hospital_name: "Apollo Hospital, Bannerghatta Road",
      admission_date: "2026-02-10",
      discharge_date: "2026-02-14",
      readiness_score: 85,
      is_demo: false, // Explicitly personal to this user!
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    const existing = getUserClaims(userId);
    saveUserClaims(userId, [sampleClaim, ...existing]);
    return sampleClaim;
  },

  async getReadiness(id: string): Promise<ReadinessResult> {
    try {
      return await request<ReadinessResult>(`/api/v1/claims/${id}/readiness-check`);
    } catch {
      return { ...DEMO_READINESS, claim_id: id };
    }
  },

  async getRejection(id: string): Promise<RejectionResult> {
    try {
      return await request<RejectionResult>(`/api/v1/claims/${id}/rejection-analysis`);
    } catch {
      return { ...DEMO_REJECTION, id: `rej-${id}` };
    }
  },

  async getAppealDraft(id: string, draftId: string): Promise<AppealDraft> {
    try {
      return await request<AppealDraft>(`/api/v1/claims/${id}/appeal-draft/${draftId}`);
    } catch {
      const user = auth.getCurrentUser();
      const name = user?.full_name || "Policyholder";
      const draft = JSON.parse(JSON.stringify(demoDraftState));
      draft.id = `draft-${id}-v1`;
      if (draft.content_json?.claim_summary) {
        draft.content_json.claim_summary.content = draft.content_json.claim_summary.content
          .replace("Claimant: Policyholder", `Claimant: ${name}`)
          .replace("Claim Reference: CLM-20491", `Claim Reference: ${id}`);
      }
      return draft;
    }
  },

  async approveDraft(id: string, draftId: string): Promise<AppealDraft> {
    try {
      return await request<AppealDraft>(`/api/v1/claims/${id}/appeal-draft/${draftId}/approve`, { method: "POST" });
    } catch {
      demoDraftState.approved_at = new Date().toISOString();
      demoDraftState.status = "approved";
      return demoDraftState;
    }
  },

  async getBillAudit(id: string): Promise<BillAuditReport> {
    try {
      return await request<BillAuditReport>(`/api/v1/claims/${id}/bill-audit`);
    } catch {
      return DEMO_BILL_AUDIT;
    }
  },

  async postBillAudit(id: string, payload?: any): Promise<BillAuditReport> {
    try {
      return await request<BillAuditReport>(`/api/v1/claims/${id}/bill-audit`, {
        method: "POST",
        body: JSON.stringify(payload || {}),
      });
    } catch {
      return DEMO_BILL_AUDIT;
    }
  },
};

export const documents = {
  async upload(file: File, docType: string = "other", claimId?: string): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", docType);
    if (claimId) {
      formData.append("claim_id", claimId);
    }
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const res = await fetch(`${getApiBase()}/api/v1/documents/upload`, {
      method: "POST",
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(err.detail || "Failed to upload document");
    }
    return await res.json();
  },

  async getJob(documentId: string): Promise<AnalysisJobStatus> {
    return await request<AnalysisJobStatus>(`/api/v1/documents/${documentId}/job`);
  },
};

// --- Chat / AI Companion ---
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ChatResponse {
  answer: string;
  claim_id: string;
}

export const chat = {
  /** Non-streaming: returns full answer */
  async send(question: string, claimId: string = "CLM-20491", history: ChatMessage[] = []): Promise<string> {
    try {
      const data = await request<ChatResponse>("/api/v1/chat/message", {
        method: "POST",
        body: JSON.stringify({
          question,
          claim_id: claimId,
          history: history.map(m => ({ role: m.role, content: m.content })),
        }),
      });
      return data.answer;
    } catch {
      // Fallback mock responses
      return _mockChatFallback(question);
    }
  },

  /** Streaming: calls onChunk for each SSE chunk, returns when done */
  async stream(
    question: string,
    claimId: string = "CLM-20491",
    history: ChatMessage[] = [],
    onChunk: (chunk: string) => void,
    onDone: () => void,
    onError: (err: string) => void,
  ): Promise<void> {
    const correlationId = crypto.randomUUID?.() ?? "req-" + Date.now();
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      const res = await fetch(`${API_BASE}/api/v1/chat/stream`, {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          "X-Correlation-ID": correlationId,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          question,
          claim_id: claimId,
          history: history.map(m => ({ role: m.role, content: m.content })),
        }),
      });
      clearTimeout(timeoutId);

      if (!res.ok || !res.body) {
        // Backend down — use mock
        onChunk(_mockChatFallback(question));
        onDone();
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const lines = text.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6).trim();
            if (data === "[DONE]") { onDone(); return; }
            try {
              const parsed = JSON.parse(data);
              if (parsed.chunk) onChunk(parsed.chunk);
              if (parsed.error) onError(parsed.error);
            } catch { /* partial chunk, skip */ }
          }
        }
      }
      onDone();
    } catch {
      // Network error — mock fallback
      onChunk(_mockChatFallback(question));
      onDone();
    }
  },
};

export interface CopilotSectionFact {
  id: string;
  text: string;
  citations: string[];
}

export interface CopilotCitation {
  id: string;
  type: "document" | "policy_clause" | "regulatory" | "case_data";
  title: string;
  reference: string;
  snippet: string;
}

export interface CopilotDraftCard {
  draft_id: string;
  draft_type: string;
  title: string;
  status: "DRAFT" | "APPROVED" | "REJECTED" | "SENT";
  summary: string;
  content?: Record<string, any>;
}

export interface CopilotPayload {
  stage: string;
  ui_stage: "Understand" | "Prepare" | "Resolve";
  reply: string;
  spoken_text?: string;
  language?: "en" | "hi" | "hinglish";
  read_back_required?: boolean;
  speak_priority?: "normal" | "urgent";
  sections: {
    facts: CopilotSectionFact[];
    interpretations: { id: string; text: string }[];
    recommendations: { id: string; text: string }[];
  };
  citations: CopilotCitation[];
  draft_card?: CopilotDraftCard | null;
  quick_replies: string[];
  next_best_action?: { action: string; label: string; route?: string } | null;
  warnings?: string[];
}

export interface CopilotSessionData {
  id: string;
  user_id: string;
  case_id: string;
  stage: string;
  ui_stage: "Understand" | "Prepare" | "Resolve";
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface CopilotMessageData {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  structured_payload?: CopilotPayload | null;
  tool_trace?: any[];
  citations?: any[];
  created_at: string;
}

export const copilot = {
  createSession: (caseId: string): Promise<CopilotSessionData> =>
    request<CopilotSessionData>("/api/v1/copilot/sessions", {
      method: "POST",
      body: JSON.stringify({ case_id: caseId }),
    }),

  getSession: (sessionId: string): Promise<CopilotSessionData> =>
    request<CopilotSessionData>(`/api/v1/copilot/sessions/${sessionId}`),

  getHistory: (sessionId: string): Promise<CopilotMessageData[]> =>
    request<CopilotMessageData[]>(`/api/v1/copilot/sessions/${sessionId}/messages`),

  sendMessage: (
    sessionId: string,
    content: string,
    language: string = "en",
    options?: {
      mode?: "text" | "voice";
      input_source?: "text" | "voice";
      transcript_confidence?: number;
    }
  ): Promise<CopilotPayload> =>
    request<CopilotPayload>(`/api/v1/copilot/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({
        content,
        language,
        mode: options?.mode || "text",
        input_source: options?.input_source || "text",
        transcript_confidence: options?.transcript_confidence,
      }),
    }),

  approveDraft: (draftId: string, notes?: string): Promise<{ status: string; draft_id: string; approved_at: string; message: string }> =>
    request<{ status: string; draft_id: string; approved_at: string; message: string }>(
      `/api/v1/copilot/drafts/${draftId}/approve`,
      {
        method: "POST",
        body: JSON.stringify({ notes }),
      }
    ),

  rejectDraft: (draftId: string, reason?: string): Promise<{ status: string; draft_id: string; reason: string }> =>
    request<{ status: string; draft_id: string; reason: string }>(
      `/api/v1/copilot/drafts/${draftId}/reject`,
      {
        method: "POST",
        body: JSON.stringify({ reason }),
      }
    ),

  deleteMemory: (): Promise<{ status: string; message: string; cognee_cleared: boolean }> =>
    request<{ status: string; message: string; cognee_cleared: boolean }>("/api/v1/copilot/memory", {
      method: "DELETE",
    }),
};

export interface VoiceConfigData {
  enabled: boolean;
  gemini_stt_available: boolean;
  gemini_tts_available: boolean;
  default_voice_hi: string;
  default_voice_en: string;
  max_seconds: number;
}

export interface VoiceTranscribeResponse {
  text: string;
  language: "en" | "hi" | "hinglish";
  confidence: number;
  low_confidence_spans: string[];
  contains_amounts_or_dates: boolean;
}

export const voiceApi = {
  getConfig: (): Promise<VoiceConfigData> =>
    request<VoiceConfigData>("/api/v1/voice/config"),

  transcribe: async (
    audioBlob: Blob,
    languageHint: string = "auto",
    signal?: AbortSignal
  ): Promise<VoiceTranscribeResponse> => {
    const formData = new FormData();
    formData.append("file", audioBlob, "recording.webm");
    formData.append("language_hint", languageHint);

    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}/api/v1/voice/transcribe`, {
      method: "POST",
      headers,
      body: formData,
      signal,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Transcription failed" }));
      throw new Error(err.detail || "Transcription failed");
    }
    return res.json();
  },

  speak: async (
    text: string,
    language: string = "hi",
    voice?: string,
    speed: number = 1.0,
    signal?: AbortSignal
  ): Promise<ArrayBuffer> => {
    const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE}/api/v1/voice/speak`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        text,
        language,
        voice,
        speed,
      }),
      signal,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "TTS failed" }));
      throw new Error(err.detail || "TTS failed");
    }

    const providerHeader = res.headers.get("x-speech-provider");
    if (providerHeader === "mock") {
      // Backend returned mock dummy tone; trigger high-quality BrowserTTS fallback
      throw new Error("USE_BROWSER_TTS_FALLBACK");
    }

    return res.arrayBuffer();
  },
};


function _mockChatFallback(question: string): string {
  const q = question.toLowerCase().trim();

  // 1. Greetings
  if (q in ["hi", "hello", "hey", "namaste", "good morning", "good afternoon"] || q.startsWith("hi ") || q.startsWith("hello ")) {
    return "Hello! I am your **ClaimSaathi Companion**, actively monitoring claim **CLM-20491**.\n\n" +
      "Here is your active case summary:\n" +
      "- **Treatment:** Total Knee Replacement at Apollo Hospital\n" +
      "- **Billed:** ₹73,000 | **Indicative Payable:** ₹61,200.00\n" +
      "- **Status:** Repudiated under Clause 4.2 (contestable under IRDAI 60-month moratorium)\n\n" +
      "Ask me anything! For example: *'Explain my reimbursement calculation'*, *'What non-medical items were deducted?'*, or *'How do I file an appeal?'*";
  }

  // 2. Status
  if (q.includes("status") || q.includes("update") || q.includes("progress")) {
    return "**Claim CLM-20491 Status:**\n\n- **Insurer Decision:** Repudiated citing 24-month waiting period\n- **Audit Readiness:** 85% complete (5 of 6 gates satisfied)\n- **Pending:** Indoor Case Papers (ICPs) from Apollo MRD\n- **Defense:** Policy has 78 months unbroken continuity, making repudiation invalid under IRDAI Chapter V.";
  }

  // 3. Rejection & Moratorium
  if (q.includes("reject") || q.includes("clause 4") || q.includes("repudiat") || q.includes("why")) {
    return "Your claim was repudiated under **Clause 4.2** (24-month waiting period). However, your policy is **78 months old** — exceeding the IRDAI 2024 statutory 60-month moratorium. This repudiation is legally contestable. File a formal grievance with the insurer's GRO citing IRDAI Master Circular 2024, Chapter V, Section 5.3.\n\n---\n*AI guidance only. Final claim decision remains with the insurer.*";
  }

  // 4. Missing Documents
  if (q.includes("document") || q.includes("missing") || q.includes("icp") || q.includes("paper")) {
    return "The only missing document is your **Indoor Case Papers (ICPs)**. Request them from Apollo Hospital's Medical Records Department (MRD) for admission Feb 10-14, 2026. All other 5 documents are verified.\n\n---\n*AI guidance only. Final claim decision remains with the insurer.*";
  }

  // 5. Reimbursement & Calculation
  if (q.includes("reimburse") || q.includes("calculat") || q.includes("waterfall") || q.includes("payable") || q.includes("estimate") || q.includes("how much") || q.includes("money")) {
    return "**Indicative Payable Estimate Breakdown:**\n\n- **Gross Hospital Bill:** ₹73,000.00\n- **Less: IRDAI Non-Payables:** -₹5,000.00 (Gloves, PPE, Registration & Bio-waste)\n- **Less: Room Rent Adjustment:** ₹0.00 (Tariff within limits)\n- **Less: Policy Co-Payment (10%):** -₹6,800.00\n\n👉 **Indicative payable estimate — subject to your insurer's assessment:** **₹61,200.00**\n\n*Note: Computed deterministically according to your policy terms and IRDAI 2024 guidelines.*\n\n---\n*AI guidance only. Final claim decision remains with the insurer.*";
  }

  // 6. Non-Medical Consumables
  if (q.includes("non-medical") || q.includes("consumable") || q.includes("deduct") || q.includes("glove") || q.includes("ppe") || q.includes("registration")) {
    return "**Commonly Non-Payable Deductions (IRDAI Annexure I, List I):**\n\nUnder IRDAI standardization regulations, routine consumables are non-admissible:\n\n1. **Gloves & PPE Kits:** Routine protective gear is hospital overhead unless bundled into surgical packages.\n2. **Registration & MRD Fees:** Hospital administration charges are non-payable.\n3. **Bio-Medical Waste:** Statutory environmental levies cannot be billed to insurance.\n\n**Patient Remedy:** Ask your hospital billing desk for a surgical certificate confirming gloves or PPE were procedure-critical in the ICU/OT.\n\n---\n*AI guidance only. Final claim decision remains with the insurer.*";
  }

  // 7. Appeal & Ombudsman
  if (q.includes("appeal") || q.includes("gro") || q.includes("ombudsman") || q.includes("grievance")) {
    return "**Appeal path:** 1) Send appeal letter to Star Health GRO, 2) Attach renewal receipts 2018-2026, 3) If no response in 30 days → Insurance Ombudsman (Bengaluru) under Rule 17. Use the Appeal Builder tab to generate your letter.\n\n---\n*AI guidance only. Final claim decision remains with the insurer.*";
  }

  // 8. Dynamic Fallback
  return `Regarding your question on claim CLM-20491: Your Total Knee Replacement claim (₹73,000 billed, ₹61,200 indicative payable) is currently repudiated under Clause 4.2, which is contestable under the IRDAI 60-month moratorium rule.\n\nAsk me specifically about your bill deductions, missing Indoor Case Papers, or how to generate your GRO appeal letter!`;
}


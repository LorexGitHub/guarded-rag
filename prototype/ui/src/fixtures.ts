import type { Doc, QueryResponse } from "./types";

export type Scenario = { id: string; label: string; question: string; res: QueryResponse };

export const scenarios: Scenario[] = [
  {
    id: "answered", label: "Answered",
    question: "How many days of parental leave does the handbook give, and who approves it?",
    res: {
      answer: "Parental leave is 16 weeks at full pay. The request goes to your line manager first, then to <PERSON_1> in People Operations for approval. Submit it at least 30 days before the start date.",
      refused: false,
      sources: [
        { doc_id: "handbook-md", source: "handbook.md", chunk_index: 14 },
        { doc_id: "leave-policy-txt", source: "leave-policy.txt", chunk_index: 2 },
      ],
      trace: {
        hits: [
          { doc_id: "handbook-md", source: "handbook.md", chunk_index: 14, score: 0.87, passed: true, text: "Parental leave: 16 weeks at full pay. Requests go to the line manager, then to <PERSON_1> (<EMAIL_ADDRESS_1>)." },
          { doc_id: "leave-policy-txt", source: "leave-policy.txt", chunk_index: 2, score: 0.79, passed: true, text: "Submit leave requests at least 30 days before the start date. Approval sits with People Operations." },
          { doc_id: "benefits-md", source: "benefits.md", chunk_index: 6, score: 0.68, passed: false, text: "Health cover continues during any approved leave of absence." },
          { doc_id: "handbook-md", source: "handbook.md", chunk_index: 3, score: 0.61, passed: false, text: "Annual leave accrues at 2.1 days per month worked." },
          { doc_id: "onboarding-txt", source: "onboarding.txt", chunk_index: 9, score: 0.55, passed: false, text: "New starters get their laptop and badge from <PERSON_2> on day one." },
        ],
        findings_in: [],
        findings_out: [{ entity_type: "PERSON", placeholder: "<PERSON_1>" }],
      },
    },
  },
  {
    id: "pii", label: "PII in question",
    question: "Can you email Marta Kowalski at marta.k@example.com about her badge, EMP-40213?",
    res: {
      answer: "Badges are issued by <PERSON_2> on a new starter's first day. Replacement badges for <EMPLOYEE_ID_1> go through the facilities desk.",
      refused: false,
      sources: [{ doc_id: "onboarding-txt", source: "onboarding.txt", chunk_index: 9 }],
      trace: {
        hits: [
          { doc_id: "onboarding-txt", source: "onboarding.txt", chunk_index: 9, score: 0.74, passed: true, text: "New starters get their laptop and badge from <PERSON_2> on day one. Replacements: facilities desk." },
          { doc_id: "handbook-md", source: "handbook.md", chunk_index: 21, score: 0.66, passed: false, text: "Contact <PERSON_3> at <PHONE_NUMBER_1> for facilities." },
        ],
        findings_in: [
          { entity_type: "PERSON", placeholder: "<PERSON_1>" },
          { entity_type: "EMAIL_ADDRESS", placeholder: "<EMAIL_ADDRESS_1>" },
          { entity_type: "EMPLOYEE_ID", placeholder: "<EMPLOYEE_ID_1>" },
        ],
        findings_out: [{ entity_type: "PERSON", placeholder: "<PERSON_2>" }, { entity_type: "EMPLOYEE_ID", placeholder: "<EMPLOYEE_ID_1>" }],
      },
    },
  },
  {
    id: "refused", label: "Refused",
    question: "What is the company's policy on cryptocurrency payroll?",
    res: {
      answer: "I can't answer that from the documents you've uploaded.",
      refused: true, sources: [],
      trace: {
        hits: [
          { doc_id: "benefits-md", source: "benefits.md", chunk_index: 11, score: 0.52, passed: false, text: "Salary is paid on the last working day of the month." },
          { doc_id: "handbook-md", source: "handbook.md", chunk_index: 8, score: 0.47, passed: false, text: "Expense claims are reimbursed with the next payroll run." },
          { doc_id: "leave-policy-txt", source: "leave-policy.txt", chunk_index: 5, score: 0.31, passed: false, text: "Unpaid leave pauses payroll for the period." },
        ],
        findings_in: [], findings_out: [],
      },
    },
  },
];

export const initialDocs: Doc[] = [
  { doc_id: "handbook-md", filename: "handbook.md", status: "ready", chunks: 38 },
  { doc_id: "leave-policy-txt", filename: "leave-policy.txt", status: "ready", chunks: 7 },
  { doc_id: "onboarding-txt", filename: "onboarding.txt", status: "ready", chunks: 12 },
  { doc_id: "benefits-md", filename: "benefits.md", status: "ready", chunks: 19 },
];

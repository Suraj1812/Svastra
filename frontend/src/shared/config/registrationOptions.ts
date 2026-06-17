import entryTerms from "../../../../data/svp_entry_terms.json";
import type { FlowMode, ReferenceTerm, ReferenceTermTag, Role } from "../types/auth";

const referenceTerms = entryTerms as ReferenceTerm[];

function byTag(tag: ReferenceTermTag) {
  return referenceTerms.filter((term) => term.tag === tag);
}

export function findReferenceTerm(options: ReferenceTerm[], conceptId: string) {
  return options.find((option) => option.conceptId === conceptId);
}

export const occupations = byTag("occupation");
export const genders = byTag("gender");
export const relationships = byTag("relationship");
export const languages = byTag("language");

export const modeLabels: Record<FlowMode, string> = {
  provider: "Mantrana Mitra",
  patient: "Rogi Mitra",
  caregiver: "Sahay Mitra",
  login: "Login",
};

export const roleDashboardLabels: Record<Role, string> = {
  provider: "Mantrana Dashboard",
  patient: "Rogi Dashboard",
  caregiver: "Sahay Dashboard",
};

export const dashboardItems: Record<Role, string[]> = {
  provider: ["Patients", "Care Plans", "Timeline", "Alerts", "Profile"],
  patient: ["Tasks", "Timeline", "Messages", "Consent Admin", "Profile"],
  caregiver: ["Patient Status", "Timeline", "Notifications", "Profile"],
};

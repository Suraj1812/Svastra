import type { FlowMode, Role } from "../types/auth";

export const occupations = [
  { value: "Physician", label: "Physician" },
  { value: "Geriatrics specialist", label: "Geriatrics specialist" },
  { value: "Obstetrician and gynaecologist", label: "Obstetrician and gynaecologist" },
  { value: "Paediatrician", label: "Paediatrician" },
  { value: "Surgeon", label: "Surgeon" },
  { value: "Dentist", label: "Dentist" },
  { value: "Nurse", label: "Nurse" },
];

export const genders = [
  { value: "Female", label: "Female" },
  { value: "Indeterminate sex", label: "Indeterminate sex" },
  { value: "Intersex", label: "Intersex" },
  { value: "Male", label: "Male" },
  { value: "Transsexual", label: "Transsexual" },
  { value: "Gender unknown", label: "Gender unknown" },
];

export const relationships = [
  { value: "Family member", label: "Family member" },
  { value: "Neighbour", label: "Neighbour" },
  { value: "Private nurse", label: "Private nurse" },
  { value: "Maid", label: "Maid" },
  { value: "Driver", label: "Driver" },
  { value: "Servant", label: "Servant" },
  { value: "Friend", label: "Friend" },
  { value: "Colleague", label: "Colleague" },
  { value: "Acquaintance", label: "Acquaintance" },
  { value: "Caregiver", label: "Caregiver" },
];

export const languages = [
  { value: "English", label: "English" },
  { value: "Hindi", label: "Hindi" },
  { value: "Bengali", label: "Bengali" },
];

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
  patient: ["Tasks", "Timeline", "Messages", "Consent", "Profile"],
  caregiver: ["Patient Status", "Timeline", "Notifications", "Profile"],
};

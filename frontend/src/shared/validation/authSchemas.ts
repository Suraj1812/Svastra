import { z } from "zod";

import {
  genders,
  languages,
  occupations,
  relationships,
} from "../config/registrationOptions";
import type { ReferenceTerm, ReferenceTermTag } from "../types/auth";

const mobileNumber = z
  .string()
  .trim()
  .min(10, "Mobile number is required")
  .max(20, "Mobile number is too long")
  .refine((value) => {
    const digits = value.replace(/\D/g, "");
    return digits.length >= 10 && digits.length <= 15;
  }, "Mobile number must contain 10 to 15 digits");

const requiredText = (label: string) => z.string().trim().min(1, `${label} is required`);
const accepted = (message: string) => z.boolean().refine((value) => value === true, message);
const referenceOptions: Record<ReferenceTermTag, ReferenceTerm[]> = {
  relationship: relationships,
  occupation: occupations,
  language: languages,
  gender: genders,
};

const referenceTermSchema = z.object({
  conceptId: z.string().trim().min(1),
  term: z.string().trim().min(1),
  tag: z.enum(["relationship", "occupation", "language", "gender"]),
});

const requiredReferenceTerm = (tag: ReferenceTermTag, label: string) =>
  referenceTermSchema.refine(
    (value) =>
      value.tag === tag &&
      referenceOptions[tag].some(
        (option) =>
          option.conceptId === value.conceptId &&
          option.term === value.term &&
          option.tag === value.tag,
      ),
    `${label} must be selected from the approved list`,
  );

export const mobileSchema = z.object({
  mobile_number: mobileNumber,
});

export const otpSchema = z.object({
  otp: z.string().trim().min(4, "OTP is required").max(8, "OTP is too long"),
});

export const providerSchema = z.object({
  full_name: requiredText("Full name"),
  mobile_number: mobileNumber,
  email_address: z.union([z.string().trim().email("Enter a valid email"), z.literal("")]).optional(),
  professional_category: requiredReferenceTerm("occupation", "Professional category"),
  registration_number: requiredText("Registration number"),
  hpid_number: z.string().trim().optional(),
  terms_accepted: accepted("Terms acceptance is required"),
});

export const patientSchema = z.object({
  full_name: requiredText("Full name"),
  mobile_number: mobileNumber,
  date_of_birth: requiredText("Date of birth"),
  gender: requiredReferenceTerm("gender", "Gender"),
  preferred_language: requiredReferenceTerm("language", "Preferred language"),
  abha_number: z.string().trim().optional(),
  emergency_contact_name: z.string().trim().optional(),
  emergency_contact_mobile: z.union([mobileNumber, z.literal("")]).optional(),
  terms_accepted: accepted("Terms acceptance is required"),
});

export const caregiverSchema = z.object({
  full_name: requiredText("Full name"),
  mobile_number: mobileNumber,
  relationship_to_patient: requiredReferenceTerm("relationship", "Relationship to patient"),
  preferred_language: requiredReferenceTerm("language", "Preferred language"),
  terms_accepted: accepted("Terms acceptance is required"),
});

export const consentSchema = z.object({
  unified_consent_accepted: accepted("Unified consent acceptance is required"),
});

export const consentDecisionSchema = z.object({
  otp: z.string().trim().min(4, "OTP is required").max(8, "OTP is too long"),
});

export const consentAliasSchema = z.object({
  alias: z.string().trim().min(1, "Alias is required").max(60, "Alias must be 60 characters or fewer"),
});

export type MobileValues = z.infer<typeof mobileSchema>;
export type OtpValues = z.infer<typeof otpSchema>;
export type ProviderValues = z.infer<typeof providerSchema>;
export type PatientValues = z.infer<typeof patientSchema>;
export type CaregiverValues = z.infer<typeof caregiverSchema>;
export type ConsentValues = z.infer<typeof consentSchema>;
export type ConsentDecisionValues = z.infer<typeof consentDecisionSchema>;
export type ConsentAliasValues = z.infer<typeof consentAliasSchema>;

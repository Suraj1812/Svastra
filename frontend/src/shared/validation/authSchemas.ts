import { z } from "zod";

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
  professional_category: requiredText("Professional category"),
  registration_number: requiredText("Registration number"),
  hpid_number: z.string().trim().optional(),
  terms_accepted: accepted("Terms acceptance is required"),
});

export const patientSchema = z.object({
  full_name: requiredText("Full name"),
  mobile_number: mobileNumber,
  date_of_birth: requiredText("Date of birth"),
  gender: requiredText("Gender"),
  preferred_language: requiredText("Preferred language"),
  abha_number: z.string().trim().optional(),
  emergency_contact_name: z.string().trim().optional(),
  emergency_contact_mobile: z.union([mobileNumber, z.literal("")]).optional(),
  terms_accepted: accepted("Terms acceptance is required"),
});

export const caregiverSchema = z.object({
  full_name: requiredText("Full name"),
  mobile_number: mobileNumber,
  relationship_to_patient: requiredText("Relationship to patient"),
  preferred_language: requiredText("Preferred language"),
  terms_accepted: accepted("Terms acceptance is required"),
});

export const consentSchema = z.object({
  unified_consent_accepted: accepted("Unified consent acceptance is required"),
});

export const consentDecisionSchema = z.object({
  otp: z.string().trim().min(4, "OTP is required").max(8, "OTP is too long"),
});

export type MobileValues = z.infer<typeof mobileSchema>;
export type OtpValues = z.infer<typeof otpSchema>;
export type ProviderValues = z.infer<typeof providerSchema>;
export type PatientValues = z.infer<typeof patientSchema>;
export type CaregiverValues = z.infer<typeof caregiverSchema>;
export type ConsentValues = z.infer<typeof consentSchema>;
export type ConsentDecisionValues = z.infer<typeof consentDecisionSchema>;

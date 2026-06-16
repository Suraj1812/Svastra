import { ApiError } from "../../../shared/api/client";
import type { FlowMode, FlowStep } from "../../../shared/types/auth";

export const storedSessionKey = "svastra-auth-result";

export function normalizePayload<T extends Record<string, unknown>>(values: T) {
  return Object.fromEntries(
    Object.entries(values).map(([key, value]) => [key, value === "" ? null : value]),
  );
}

export function getErrorMessage(error: unknown) {
  if (error instanceof ApiError) {
    return error.requestId ? `${error.message} (${error.requestId})` : error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong";
}

export function getSteps(mode: FlowMode) {
  if (mode === "login") {
    return ["Mobile Number", "OTP Verification", "Dashboard"];
  }
  if (mode === "patient") {
    return [
      "Mobile Number",
      "OTP Verification",
      "Patient Registration Form",
      "Unified Consent Display",
      "Patient Dashboard",
    ];
  }
  const registrationLabel =
    mode === "provider" ? "Provider Registration Form" : "Caregiver Registration Form";
  const dashboardLabel = mode === "provider" ? "Provider Dashboard" : "Caregiver Dashboard";
  return ["Mobile Number", "OTP Verification", registrationLabel, dashboardLabel];
}

export function stepIndex(step: FlowStep, mode: FlowMode) {
  if (step === "mobile") return 0;
  if (step === "otp") return 1;
  if (step === "registration") return 2;
  if (step === "consent") return 3;
  return mode === "patient" ? 4 : mode === "login" ? 2 : 3;
}

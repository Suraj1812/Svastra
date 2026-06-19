import { useEffect, useMemo, useState } from "react";

import { postJson } from "../../../shared/api/client";
import type {
  AuthResult,
  FlowMode,
  FlowStep,
  ValidateSessionResult,
} from "../../../shared/types/auth";
import type {
  CaregiverValues,
  MobileValues,
  OtpValues,
  PatientValues,
  ProviderValues,
} from "../../../shared/validation/authSchemas";
import {
  getErrorMessage,
  getSteps,
  normalizePayload,
  stepIndex,
  storedSessionKey,
} from "./workflowUtils";

function readStoredAuth() {
  try {
    const stored = window.localStorage.getItem(storedSessionKey);
    return stored ? (JSON.parse(stored) as AuthResult) : null;
  } catch {
    return null;
  }
}

export function useAuthWorkflow() {
  const [mode, setMode] = useState<FlowMode>("login");
  const [step, setStep] = useState<FlowStep>("mobile");
  const [mobile, setMobile] = useState("");
  const [auth, setAuth] = useState<AuthResult | null>(() => readStoredAuth());
  const [pendingPatient, setPendingPatient] = useState<PatientValues | null>(null);
  const [loading, setLoading] = useState(false);
  const [booting, setBooting] = useState(Boolean(auth));
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const steps = useMemo(() => getSteps(mode), [mode]);
  const activeStep = useMemo(() => stepIndex(step, mode), [mode, step]);

  useEffect(() => {
    if (!auth?.session.session_token) {
      setBooting(false);
      return;
    }

    postJson<ValidateSessionResult>("/auth/session/validate", {
      session_token: auth.session.session_token,
    })
      .then((data) => {
        const nextAuth: AuthResult = {
          user: data.user,
          session: data.session,
          dashboard_route: data.dashboard_route,
          consent: auth.consent,
        };
        setAuth(nextAuth);
        setMode(data.user.role);
        setStep("dashboard");
      })
      .catch(() => {
        window.localStorage.removeItem(storedSessionKey);
        setAuth(null);
        setStep("mobile");
      })
      .finally(() => setBooting(false));
  }, []);

  function persistAuth(result: AuthResult) {
    setAuth(result);
    setMode(result.user.role);
    setStep("dashboard");
    window.localStorage.setItem(storedSessionKey, JSON.stringify(result));
  }

  function resetFlow(nextMode = mode) {
    setMode(nextMode);
    setStep("mobile");
    setMobile("");
    setPendingPatient(null);
    setError(null);
    setSuccess(null);
  }

  function switchMode(nextMode: FlowMode) {
    window.localStorage.removeItem(storedSessionKey);
    setAuth(null);
    resetFlow(nextMode);
  }

  async function runAction<T>(action: () => Promise<T>, message?: string) {
    setLoading(true);
    setError(null);
    try {
      const result = await action();
      if (message) {
        setSuccess(message);
      }
      return result;
    } catch (actionError) {
      setError(getErrorMessage(actionError));
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function handleSendOtp(values: MobileValues) {
    const result = await runAction(
      () => postJson("/auth/otp/send", values),
      "OTP request accepted",
    );
    if (result) {
      setMobile(values.mobile_number);
      setStep("otp");
    }
  }

  async function handleVerifyOtp(values: OtpValues) {
    const verified = await runAction(() =>
      postJson("/auth/otp/verify", { mobile_number: mobile, otp: values.otp }),
    );
    if (!verified) return;

    if (mode === "login") {
      const result = await runAction<AuthResult>(
        () => postJson<AuthResult>("/auth/login", { mobile_number: mobile }),
        "Login completed",
      );
      if (result) {
        persistAuth(result);
      }
      return;
    }

    setSuccess("OTP verified");
    setStep("registration");
  }

  async function handleProviderRegistration(values: ProviderValues) {
    const result = await runAction<AuthResult>(
      () =>
        postJson<AuthResult>(
          "/auth/register/provider",
          normalizePayload(values) as ProviderValues,
        ),
      "Provider registration completed",
    );
    if (result) {
      persistAuth(result);
    }
  }

  function handlePatientForm(values: PatientValues) {
    setPendingPatient(values);
    setStep("consent");
    setError(null);
  }

  async function handleConsentAccept() {
    if (!pendingPatient) {
      setError("Patient registration details are missing");
      setStep("registration");
      return;
    }

    const result = await runAction<AuthResult>(
      () =>
        postJson<AuthResult>("/auth/register/patient", {
          ...normalizePayload(pendingPatient),
          unified_consent_accepted: true,
        }),
      "Patient registration completed",
    );
    if (result) {
      persistAuth(result);
    }
  }

  async function handleCaregiverRegistration(values: CaregiverValues) {
    const result = await runAction<AuthResult>(
      () =>
        postJson<AuthResult>(
          "/auth/register/caregiver",
          normalizePayload(values) as CaregiverValues,
        ),
      "Caregiver registration completed",
    );
    if (result) {
      persistAuth(result);
    }
  }

  async function handleLogout() {
    if (!auth) return;
    const result = await runAction<{ logged_out: boolean }>(
      () => postJson("/auth/logout", { session_token: auth.session.session_token }),
      "Logged out",
    );
    if (result) {
      window.localStorage.removeItem(storedSessionKey);
      setAuth(null);
      resetFlow("login");
    }
  }

  return {
    activeStep,
    auth,
    booting,
    error,
    loading,
    mobile,
    mode,
    step,
    steps,
    success,
    handleCaregiverRegistration,
    handleConsentAccept,
    handleLogout,
    handlePatientForm,
    handleProviderRegistration,
    handleSendOtp,
    handleVerifyOtp,
    setStep,
    setSuccess,
    switchMode,
  };
}

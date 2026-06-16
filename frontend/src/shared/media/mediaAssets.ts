import type { FlowStep } from "../types/auth";

export type MediaAsset = {
  poster: string;
  video: string;
  label: string;
  credit: string;
};

export const workflowMedia: Record<FlowStep, MediaAsset> = {
  mobile: {
    poster: "/media/clinic-consultation.jpg",
    video: "/media/clinic-consultation.webm",
    label: "Doctor consulting with a patient in a clinic",
    credit: "Clinic consultation",
  },
  otp: {
    poster: "/media/telehealth-login.jpg",
    video: "/media/telehealth-login.webm",
    label: "Clinician conducting a telehealth consultation",
    credit: "Secure telehealth",
  },
  registration: {
    poster: "/media/care-plan-review.jpg",
    video: "/media/care-plan-review.webm",
    label: "Clinical team reviewing patient details",
    credit: "Care registration",
  },
  consent: {
    poster: "/media/care-plan-review.jpg",
    video: "/media/care-plan-review.webm",
    label: "Clinicians reviewing care documentation",
    credit: "Consent review",
  },
  dashboard: {
    poster: "/media/clinical-team.jpg",
    video: "/media/clinical-team.webm",
    label: "Healthcare workers discussing medical notes",
    credit: "Care operations",
  },
};

export const dashboardMedia = workflowMedia.dashboard;

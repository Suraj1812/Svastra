import { useEffect, useMemo, useState, type ReactElement } from "react";
import {
  Alert,
  Box,
  Button,
  Divider,
  Grid,
  Paper,
  Skeleton,
  Stack,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import AssignmentTurnedInIcon from "@mui/icons-material/AssignmentTurnedIn";
import EventNoteIcon from "@mui/icons-material/EventNote";
import FolderSharedIcon from "@mui/icons-material/FolderShared";
import HealthAndSafetyIcon from "@mui/icons-material/HealthAndSafety";
import LogoutIcon from "@mui/icons-material/Logout";
import NotificationsActiveIcon from "@mui/icons-material/NotificationsActive";
import PersonIcon from "@mui/icons-material/Person";
import PrivacyTipIcon from "@mui/icons-material/PrivacyTip";

import { getJsonWithSession } from "../../shared/api/client";
import { dashboardItems, roleDashboardLabels } from "../../shared/config/registrationOptions";
import type {
  AuthResult,
  ConsentListResult,
  ConsentRequestsResult,
  ConsentStatusResult,
  PermissionsResult,
  RelationshipConsentSummary,
  Role,
} from "../../shared/types/auth";
import { ConsentWorkspace } from "./components/ConsentWorkspace";
import { CarePlanWorkspace } from "./components/CarePlanWorkspace";
import { DashboardEmptyState } from "./components/DashboardEmptyState";
import { PermissionDenied } from "./components/PermissionDenied";
import { RelationshipWorkspace } from "./components/RelationshipWorkspace";

type DashboardShellProps = {
  auth: AuthResult;
  onLogout: () => void;
  loggingOut: boolean;
};

const iconByItem: Record<string, ReactElement> = {
  Patients: <FolderSharedIcon />,
  "Care Plans": <AssignmentTurnedInIcon />,
  Timeline: <EventNoteIcon />,
  Alerts: <NotificationsActiveIcon />,
  Profile: <PersonIcon />,
  Tasks: <AssignmentTurnedInIcon />,
  Messages: <NotificationsActiveIcon />,
  "Consent Admin": <PrivacyTipIcon />,
  "Patient Status": <HealthAndSafetyIcon />,
  Notifications: <NotificationsActiveIcon />,
};

const permissionByItem: Partial<Record<Role, Partial<Record<string, string>>>> = {
  provider: {
    Patients: "VIEW_PATIENTS",
    "Care Plans": "CREATE_CARE_PLANS",
    Timeline: "VIEW_TIMELINE",
    Alerts: "VIEW_ALERTS",
  },
  patient: {
    Tasks: "VIEW_TASKS",
    Timeline: "VIEW_TIMELINE",
    "Consent Admin": "MANAGE_CONSENT",
  },
  caregiver: {
    "Patient Status": "VIEW_PATIENT_STATUS",
    Timeline: "VIEW_TIMELINE",
    Notifications: "RECEIVE_NOTIFICATIONS",
  },
};

export function DashboardShell({ auth, onLogout, loggingOut }: DashboardShellProps) {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [permissionsLoading, setPermissionsLoading] = useState(true);
  const [consentStatus, setConsentStatus] = useState<ConsentStatusResult | null>(null);
  const [activeConsents, setActiveConsents] = useState<RelationshipConsentSummary[]>([]);
  const [pendingConsents, setPendingConsents] = useState<RelationshipConsentSummary[]>([]);
  const [inactiveConsents, setInactiveConsents] = useState<RelationshipConsentSummary[]>([]);
  const [dashboardError, setDashboardError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const items = dashboardItems[auth.user.role as Role];
  const selectedItem = items[activeTab] || items[0];

  useEffect(() => {
    const timer = window.setTimeout(() => setLoading(false), 550);
    return () => window.clearTimeout(timer);
  }, [auth.user.id]);

  useEffect(() => {
    let active = true;
    const sessionToken = auth.session.session_token;
    setPermissionsLoading(true);
    setDashboardError(null);

    async function loadDashboardContracts() {
      try {
        const permissionsResult = await getJsonWithSession<PermissionsResult>(
          "/me/permissions",
          sessionToken,
        );
        if (!active) return;
        setPermissions(permissionsResult.permissions.map((permission) => permission.code));

        if (auth.user.role === "patient") {
          const [statusResult, activeResult, pendingResult, inactiveResult] = await Promise.all([
            getJsonWithSession<ConsentStatusResult>("/me/consent-status", sessionToken),
            getJsonWithSession<ConsentListResult>("/consent/active", sessionToken),
            getJsonWithSession<ConsentRequestsResult>("/consent/pending", sessionToken),
            getJsonWithSession<ConsentListResult>("/consent/inactive", sessionToken),
          ]);
          if (!active) return;
          setConsentStatus(statusResult);
          setActiveConsents(activeResult.consents);
          setPendingConsents(pendingResult.requests);
          setInactiveConsents(inactiveResult.consents);
        } else {
          setConsentStatus(null);
          setActiveConsents([]);
          setPendingConsents([]);
          setInactiveConsents([]);
        }
      } catch (error) {
        if (active) {
          setDashboardError(error instanceof Error ? error.message : "Dashboard data failed to load");
        }
      } finally {
        if (active) {
          setPermissionsLoading(false);
        }
      }
    }

    loadDashboardContracts();
    return () => {
      active = false;
    };
  }, [auth.session.session_token, auth.user.role, refreshKey]);

  const emptyStateText = useMemo(() => {
    if (auth.user.role === "provider") {
      return "No patients are linked yet.";
    }
    if (auth.user.role === "patient") {
      return "No care tasks are assigned yet.";
    }
    return "No patient status updates are available yet.";
  }, [auth.user.role]);

  const requiredPermission = permissionByItem[auth.user.role]?.[selectedItem];
  const hasSectionPermission =
    !requiredPermission || permissions.includes(requiredPermission) || permissionsLoading;

  return (
    <Stack spacing={{ xs: 2.5, md: 3.5 }}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", md: "center" }}
        gap={2}
      >
        <Stack spacing={0.5}>
          <Typography variant="caption" color="text.secondary">
            {auth.dashboard_route}
          </Typography>
          <Typography variant="h1">{roleDashboardLabels[auth.user.role]}</Typography>
          <Typography color="text.secondary">{auth.user.full_name}</Typography>
        </Stack>
        <Button
          variant="outlined"
          color="inherit"
          startIcon={<LogoutIcon />}
          onClick={onLogout}
          disabled={loggingOut}
        >
          Logout
        </Button>
      </Stack>

      {auth.consent ? (
        <Alert severity="success" sx={{ maxWidth: 620 }}>
          Platform consent recorded: {auth.consent.consent_version}
        </Alert>
      ) : null}

      {dashboardError ? (
        <Alert severity="error" sx={{ maxWidth: 620 }}>
          {dashboardError}
        </Alert>
      ) : null}

      <Paper
        variant="outlined"
        sx={{
          overflow: "hidden",
          borderColor: "rgba(15, 118, 110, 0.14)",
          boxShadow: "0 24px 70px rgba(15, 23, 42, 0.07)",
        }}
      >
        <Tabs
          value={activeTab}
          onChange={(_, value) => setActiveTab(value)}
          variant="scrollable"
          scrollButtons="auto"
          aria-label={`${roleDashboardLabels[auth.user.role]} sections`}
          sx={{
            px: { xs: 1, md: 2 },
            pt: 1,
            minHeight: 58,
            "& .MuiTab-root": {
              minHeight: 50,
              textTransform: "none",
              fontWeight: 760,
            },
          }}
        >
          {items.map((item) => (
            <Tab
              key={item}
              icon={iconByItem[item]}
              iconPosition="start"
              label={item}
            />
          ))}
        </Tabs>
        <Divider />
        <Box sx={{ p: { xs: 2.5, sm: 3, md: 4 }, minHeight: 430 }}>
          {loading || permissionsLoading ? (
            <Grid container spacing={3} aria-label="Loading dashboard section">
              <Grid size={{ xs: 12, md: 6 }}>
                <Stack spacing={2}>
                  <Skeleton variant="rounded" width="52%" height={28} />
                  <Skeleton variant="rounded" width="100%" height={82} />
                  <Skeleton variant="rounded" width="88%" height={82} />
                  <Skeleton variant="rounded" width="70%" height={82} />
                </Stack>
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <Skeleton variant="rounded" width="100%" height={280} />
              </Grid>
            </Grid>
          ) : !hasSectionPermission ? (
            <PermissionDenied />
          ) : selectedItem === "Consent Admin" && auth.user.role === "patient" ? (
            <Stack spacing={4}>
              <ConsentWorkspace
                consentStatus={consentStatus}
                activeConsents={activeConsents}
                pendingRequests={pendingConsents}
                inactiveConsents={inactiveConsents}
                sessionToken={auth.session.session_token}
                onRefresh={() => setRefreshKey((current) => current + 1)}
              />
              <RelationshipWorkspace
                role="patient"
                sessionToken={auth.session.session_token}
                pendingCount={pendingConsents.length}
              />
            </Stack>
          ) : selectedItem === "Patients" && auth.user.role === "provider" ? (
            <RelationshipWorkspace
              role="provider"
              sessionToken={auth.session.session_token}
            />
          ) : selectedItem === "Patient Status" && auth.user.role === "caregiver" ? (
            <RelationshipWorkspace
              role="caregiver"
              sessionToken={auth.session.session_token}
            />
          ) : selectedItem === "Care Plans" && auth.user.role === "provider" ? (
            <CarePlanWorkspace sessionToken={auth.session.session_token} />
          ) : (
            <Grid
              container
              justifyContent="center"
              alignItems="center"
              sx={{ minHeight: 320 }}
            >
              <Grid size={{ xs: 12 }}>
                <DashboardEmptyState
                  icon={iconByItem[selectedItem]}
                  selectedItem={selectedItem}
                  emptyStateText={emptyStateText}
                />
              </Grid>
            </Grid>
          )}
        </Box>
      </Paper>
    </Stack>
  );
}

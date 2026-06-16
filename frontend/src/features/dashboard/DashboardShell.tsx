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

import { dashboardItems, roleDashboardLabels } from "../../shared/config/registrationOptions";
import { dashboardMedia } from "../../shared/media/mediaAssets";
import type { AuthResult, Role } from "../../shared/types/auth";

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
  "Patient Status": <HealthAndSafetyIcon />,
  Notifications: <NotificationsActiveIcon />,
};

export function DashboardShell({ auth, onLogout, loggingOut }: DashboardShellProps) {
  const [activeTab, setActiveTab] = useState(0);
  const [loading, setLoading] = useState(true);
  const items = dashboardItems[auth.user.role as Role];
  const selectedItem = items[activeTab] || items[0];

  useEffect(() => {
    const timer = window.setTimeout(() => setLoading(false), 550);
    return () => window.clearTimeout(timer);
  }, [auth.user.id]);

  const emptyStateText = useMemo(() => {
    if (auth.user.role === "provider") {
      return "No patients are linked yet.";
    }
    if (auth.user.role === "patient") {
      return "No care tasks are assigned yet.";
    }
    return "No patient status updates are available yet.";
  }, [auth.user.role]);

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
          {loading ? (
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
          ) : (
            <Grid
              container
              justifyContent="center"
              alignItems="center"
              sx={{ minHeight: 320 }}
            >
              <Grid size={{ xs: 12 }}>
                <Stack
                  spacing={2.5}
                  alignItems="center"
                  justifyContent="center"
                  textAlign="center"
                  sx={{
                    minHeight: 320,
                    maxWidth: 520,
                    mx: "auto",
                  }}
                >
                  <Box
                    aria-hidden
                    sx={{
                      width: 64,
                      height: 64,
                      borderRadius: 3,
                      display: "grid",
                      placeItems: "center",
                      color: "primary.main",
                      backgroundColor: "#e8f7f4",
                      border: "1px solid #bfe9e1",
                    }}
                  >
                    {iconByItem[selectedItem]}
                  </Box>

                  <Typography variant="h4" fontWeight={700}>
                    {selectedItem}
                  </Typography>

                  <Typography
                    variant="body1"
                    color="text.secondary"
                    sx={{ maxWidth: 420 }}
                  >
                    {emptyStateText}
                  </Typography>

                  <Alert
                    severity="info"
                    sx={{
                      width: "100%",
                      maxWidth: 500,
                    }}
                  >
                    This section will display information when data becomes available.
                  </Alert>
                </Stack>
              </Grid>
            </Grid>
          )}
        </Box>
      </Paper>
    </Stack>
  );
}

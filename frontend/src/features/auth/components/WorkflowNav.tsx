import { useState, type ReactElement, type MouseEvent } from "react";
import {
  Button,
  Menu,
  MenuItem,
  Paper,
  Stack,
} from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import Diversity3Icon from "@mui/icons-material/Diversity3";
import FavoriteBorderIcon from "@mui/icons-material/FavoriteBorder";
import LoginIcon from "@mui/icons-material/Login";
import MedicalServicesIcon from "@mui/icons-material/MedicalServices";

import { BrandMark } from "../../../shared/components/BrandMark";
import type { FlowMode } from "../../../shared/types/auth";

type WorkflowNavProps = {
  activeStep: number;
  mode: FlowMode;
  steps: string[];
  onModeChange: (mode: FlowMode) => void;
};

const modeIcons: Record<FlowMode, ReactElement> = {
  provider: <MedicalServicesIcon fontSize="small" />,
  patient: <FavoriteBorderIcon fontSize="small" />,
  caregiver: <Diversity3Icon fontSize="small" />,
  login: <LoginIcon fontSize="small" />,
};

export function WorkflowNav({
  mode,
  onModeChange,
}: WorkflowNavProps) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleOpen = (event: MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleRegisterSelect = (role: FlowMode) => {
    onModeChange(role);
    handleClose();
  };

  const registerLabel =
    mode === "patient"
      ? "Rogi Mitra"
      : mode === "provider"
        ? "Mantrana Mitra"
        : mode === "caregiver"
          ? "Sahay Mitra"
          : "Register";

  return (
    <Paper
      component="header"
      square
      elevation={0}
      sx={{
        borderBottom: "1px solid",
        borderColor: "divider",
        backgroundColor: "rgba(255,255,255,0.92)",
        backdropFilter: "blur(16px)",
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}
    >
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={{ xs: 2, md: 3 }}
        alignItems={{ xs: "stretch", md: "center" }}
        justifyContent="space-between"
        sx={{
          width: "100%",
          maxWidth: 1280,
          mx: "auto",
          px: { xs: 2, sm: 3, md: 4 },
          py: { xs: 1.75, md: 2 },
        }}
      >
        <BrandMark />

        <Stack
          direction="row"
          spacing={1.5}
          justifyContent={{ xs: "stretch", md: "flex-end" }}
        >
          <Button
            variant={
              mode === "patient" ||
                mode === "provider" ||
                mode === "caregiver"
                ? "contained"
                : "outlined"
            }
            endIcon={<KeyboardArrowDownIcon />}
            onClick={handleOpen}
            sx={{
              minWidth: 160,
              borderRadius: 1,
            }}
          >
            {registerLabel}
          </Button>

          <Button
            variant={mode === "login" ? "contained" : "outlined"}
            startIcon={modeIcons.login}
            onClick={() => onModeChange("login")}
            sx={{
              minWidth: 120,
              borderRadius: 1,
            }}
          >
            Login
          </Button>

          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleClose}
          >
            <MenuItem onClick={() => handleRegisterSelect("patient")}>
              <Stack direction="row" spacing={1} alignItems="center">
                {modeIcons.patient}
                <span>Rogi Mitra</span>
              </Stack>
            </MenuItem>

            <MenuItem onClick={() => handleRegisterSelect("provider")}>
              <Stack direction="row" spacing={1} alignItems="center">
                {modeIcons.provider}
                <span>Mantrana Mitra</span>
              </Stack>
            </MenuItem>

            <MenuItem onClick={() => handleRegisterSelect("caregiver")}>
              <Stack direction="row" spacing={1} alignItems="center">
                {modeIcons.caregiver}
                <span>Sahay Mitra</span>
              </Stack>
            </MenuItem>
          </Menu>
        </Stack>
      </Stack>
    </Paper>
  );
}
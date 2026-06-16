import { Box, Chip, Paper, Stack, Typography } from "@mui/material";

import { modeLabels } from "../../../shared/config/registrationOptions";
import { workflowMedia } from "../../../shared/media/mediaAssets";
import type { FlowMode, FlowStep } from "../../../shared/types/auth";

type ClinicalMediaPanelProps = {
  mode: FlowMode;
  step: FlowStep;
};

export function ClinicalMediaPanel({
  mode,
  step,
}: ClinicalMediaPanelProps) {
  const media = workflowMedia[step];

  return (
    <Paper
      variant="outlined"
      sx={{
        flex: 1,
        height: "100%",
        minHeight: { xs: 520, lg: 580 },
        overflow: "hidden",
        position: "relative",
        borderColor: "rgba(15, 118, 110, 0.14)",
        boxShadow: "0 24px 70px rgba(15, 23, 42, 0.06)",
        backgroundColor: "background.paper",
      }}
    >
      <Box
        component="video"
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        poster={media.poster}
        aria-label={media.label}
        sx={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectFit: "cover",
        }}
      >
        <source src={media.video} type="video/webm" />
      </Box>

      <Box
        sx={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(180deg, rgba(15,23,42,0.18) 0%, rgba(15,23,42,0.42) 45%, rgba(15,23,42,0.78) 100%)",
        }}
      />

      <Stack
        spacing={2}
        justifyContent="flex-end"
        alignItems="flex-start"
        textAlign="left"
        sx={{
          position: "relative",
          zIndex: 2,
          height: "100%",
          p: { xs: 3, md: 5 },
          color: "#ffffff",
        }}
      >
        <Stack
          direction="row"
          spacing={1}
          justifyContent="center"
          flexWrap="wrap"
        >
          <Chip
            size="small"
            label={modeLabels[mode]}
            variant="outlined"
            sx={{
              color: "#ffffff",
              borderColor: "rgba(255,255,255,0.35)",
              backgroundColor: "rgba(255,255,255,0.12)",
              backdropFilter: "blur(12px)",
            }}
          />
          <Chip
            size="small"
            label="SVASTRA+"
            variant="outlined"
            sx={{
              color: "#ffffff",
              borderColor: "rgba(255,255,255,0.35)",
              backgroundColor: "rgba(255,255,255,0.12)",
              backdropFilter: "blur(12px)",
            }}
          />
        </Stack>

        <Typography
          variant="h3"
          fontWeight={800}
          sx={{
            color: "#ffffff",
            lineHeight: 1.15,
            maxWidth: 420,
          }}
        >
          {media.label}
        </Typography>

        <Typography
          variant="body1"
          sx={{
            color: "rgba(255,255,255,0.88)",
            lineHeight: 1.8,
            maxWidth: 420,
          }}
        >
          Secure healthcare identity, consent management, and role-based access
          designed for providers, patients, and caregivers.
        </Typography>
      </Stack>
    </Paper>
  );
}
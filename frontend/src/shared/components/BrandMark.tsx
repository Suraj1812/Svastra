import { Box, Stack, Typography } from "@mui/material";
import HealthAndSafetyIcon from "@mui/icons-material/HealthAndSafety";

type BrandMarkProps = {
  compact?: boolean;
};

export function BrandMark({ compact = false }: BrandMarkProps) {
  return (
    <Stack direction="row" spacing={1.25} alignItems="center" minWidth={0}>
      <Box
        aria-hidden
        sx={{
          display: "grid",
          placeItems: "center",
          color: "primary.dark",
        }}
      >
        <HealthAndSafetyIcon fontSize={compact ? "small" : "large"} />
      </Box>
      <Stack spacing={0} minWidth={0}>
        <Typography
          component="div"
          sx={{
            color: "text.primary",
            fontSize: compact ? "1.05rem" : "1.2rem",
            fontWeight: 820,
            letterSpacing: 0,
            lineHeight: 1.1,
          }}
        >
          SVASTRA+
        </Typography>
        <Typography variant="caption" color="text.secondary" noWrap>
          Identity layer
        </Typography>
      </Stack>
    </Stack>
  );
}

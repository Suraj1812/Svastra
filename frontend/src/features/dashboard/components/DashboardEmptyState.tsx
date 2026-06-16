import type { ReactElement } from "react";
import { Box, Stack, Typography } from "@mui/material";

type DashboardEmptyStateProps = {
  icon: ReactElement;
  selectedItem: string;
  emptyStateText: string;
};

export function DashboardEmptyState({
  icon,
  selectedItem,
  emptyStateText,
}: DashboardEmptyStateProps) {
  return (
    <Stack
      spacing={2.5}
      alignItems="center"
      justifyContent="center"
      textAlign="center"
      sx={{ minHeight: 320, maxWidth: 520, mx: "auto" }}
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
        {icon}
      </Box>

      <Typography variant="h2">{selectedItem}</Typography>

      <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 420 }}>
        {emptyStateText}
      </Typography>
    </Stack>
  );
}

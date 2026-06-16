import { Alert, Box, Stack, Typography } from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";

export function PermissionDenied() {
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
          color: "error.main",
          backgroundColor: "#fef2f2",
          border: "1px solid #fecaca",
        }}
      >
        <LockOutlinedIcon />
      </Box>
      <Typography variant="h2">Permission Denied</Typography>
      <Alert severity="error" sx={{ width: "100%", maxWidth: 500 }}>
        You do not have permission to access this section.
      </Alert>
    </Stack>
  );
}

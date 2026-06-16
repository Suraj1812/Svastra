import { alpha, createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#0f766e",
      dark: "#0b5f5a",
      light: "#99f6e4",
    },
    secondary: {
      main: "#1d4ed8",
      dark: "#1e3a8a",
      light: "#bfdbfe",
    },
    info: {
      main: "#0369a1",
    },
    success: {
      main: "#15803d",
    },
    warning: {
      main: "#b45309",
    },
    error: {
      main: "#b91c1c",
    },
    background: {
      default: "#f7faf9",
      paper: "#ffffff",
    },
    text: {
      primary: "#0f172a",
      secondary: "#475569",
    },
    divider: "#d9e4e4",
  },
  shape: {
    borderRadius: 8,
  },
  typography: {
    fontFamily:
      'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: {
      fontSize: "1.9rem",
      fontWeight: 820,
      lineHeight: 1.16,
      letterSpacing: 0,
    },
    h2: {
      fontSize: "1.45rem",
      fontWeight: 780,
      lineHeight: 1.22,
      letterSpacing: 0,
    },
    h3: {
      fontSize: "1.08rem",
      fontWeight: 760,
      lineHeight: 1.3,
      letterSpacing: 0,
    },
    body1: {
      lineHeight: 1.55,
      letterSpacing: 0,
    },
    body2: {
      lineHeight: 1.5,
      letterSpacing: 0,
    },
    caption: {
      letterSpacing: 0,
      fontWeight: 650,
    },
    button: {
      textTransform: "none",
      fontWeight: 740,
      letterSpacing: 0,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 8,
          minHeight: 44,
          boxShadow: "none",
          "&:focus-visible": {
            outline: `3px solid ${alpha(theme.palette.primary.main, 0.22)}`,
            outlineOffset: 2,
          },
        }),
        containedPrimary: {
          boxShadow: "0 10px 24px rgba(15, 118, 110, 0.18)",
          "&:hover": {
            boxShadow: "0 12px 28px rgba(15, 118, 110, 0.24)",
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          backgroundImage: "none",
        },
      },
    },
    MuiToggleButton: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 8,
          borderColor: theme.palette.divider,
          color: theme.palette.text.secondary,
          "&.Mui-selected": {
            color: theme.palette.primary.dark,
            backgroundColor: alpha(theme.palette.primary.main, 0.1),
            borderColor: alpha(theme.palette.primary.main, 0.42),
          },
          "&:focus-visible": {
            outline: `3px solid ${alpha(theme.palette.primary.main, 0.2)}`,
            outlineOffset: 2,
          },
        }),
      },
    },
    MuiTextField: {
      defaultProps: {
        fullWidth: true,
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 8,
          backgroundColor: "#ffffff",
          transition: theme.transitions.create(["border-color", "box-shadow"], {
            duration: theme.transitions.duration.shorter,
          }),
          "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
            borderColor: theme.palette.primary.main,
            boxShadow: `0 0 0 3px ${alpha(theme.palette.primary.main, 0.12)}`,
          },
        }),
        input: {
          minHeight: 24,
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        select: {
          minHeight: 24,
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: ({ theme }) => ({
          borderRadius: 8,
          border: `1px solid ${alpha(theme.palette.info.main, 0.18)}`,
        }),
      },
    },
  },
});

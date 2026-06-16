import type { ReactNode } from "react";
import { Button, CircularProgress, type ButtonProps } from "@mui/material";

type SubmitButtonProps = ButtonProps & {
  loading: boolean;
  children: string;
  icon?: ReactNode;
};

export function SubmitButton({ loading, children, icon, disabled, ...props }: SubmitButtonProps) {
  return (
    <Button
      type="submit"
      variant="contained"
      size="large"
      fullWidth
      disabled={loading || disabled}
      startIcon={loading ? <CircularProgress size={18} color="inherit" /> : icon}
      {...props}
    >
      {children}
    </Button>
  );
}

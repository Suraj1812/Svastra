import { useCallback, useEffect, useRef, useState } from "react";
import { Alert, Button, Chip, Grid, Paper, Stack, Typography } from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";

import { downloadWithSession, getJsonWithSession, postJsonWithSession } from "../../../shared/api/client";
import type { CareTask } from "../../../shared/types/auth";

export function ProviderTasks({ sessionToken }: { sessionToken: string }) {
  const [tasks, setTasks] = useState<CareTask[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const load = useCallback(async () => {
    try {
      const result = await getJsonWithSession<{ tasks: CareTask[] }>("/provider/tasks", sessionToken);
      if (mounted.current) setTasks(result.tasks);
    } catch (loadError) {
      if (mounted.current) setError(loadError instanceof Error ? loadError.message : "Tasks could not be loaded");
    }
  }, [sessionToken]);

  useEffect(() => { void load(); }, [load]);

  async function checkOverdue() {
    setWorking(true);
    try {
      await postJsonWithSession("/provider/tasks/evaluate-overdue", { patient_id: null }, sessionToken);
      await load();
    } catch (checkError) {
      setError(checkError instanceof Error ? checkError.message : "Could not check overdue tasks");
    } finally {
      setWorking(false);
    }
  }

  async function openReport(task: CareTask) {
    const attachment = task.response?.attachment;
    if (!attachment) return;
    try {
      const blob = await downloadWithSession(`/attachments/${attachment.attachment_id}`, sessionToken);
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Report could not be opened");
    }
  }

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1.5}>
        <Stack spacing={0.5}>
          <Typography variant="h2">Patient Tasks</Typography>
          <Typography color="text.secondary">Pending and completed care.</Typography>
        </Stack>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => void checkOverdue()} disabled={working}>Check due tasks</Button>
      </Stack>
      {error ? <Alert severity="error" onClose={() => setError(null)}>{error}</Alert> : null}
      {tasks.length === 0 ? <Alert severity="info">No tasks yet.</Alert> : (
        <Grid container spacing={2}>
          {tasks.map((task) => (
            <Grid key={task.task_id} size={{ xs: 12, md: 6 }}>
              <Paper variant="outlined" sx={{ p: 2.25, height: "100%" }}>
                <Stack spacing={1.25}>
                  <Stack direction="row" justifyContent="space-between" gap={1}>
                    <Stack spacing={0.25}>
                      <Typography variant="h3">{task.advisory}</Typography>
                      <Typography color="text.secondary">{task.patient.full_name}</Typography>
                    </Stack>
                    <Chip size="small" color={task.execution_status === "pending" ? "warning" : task.execution_status === "missed" ? "error" : "success"} label={task.execution_status.replaceAll("_", " ")} />
                  </Stack>
                  {task.response ? <Typography>{task.response.response_status.replaceAll("_", " ")}</Typography> : <Typography color="text.secondary">Waiting for response</Typography>}
                  {task.response?.attachment ? <Button variant="outlined" onClick={() => void openReport(task)}>Open report</Button> : null}
                </Stack>
              </Paper>
            </Grid>
          ))}
        </Grid>
      )}
    </Stack>
  );
}

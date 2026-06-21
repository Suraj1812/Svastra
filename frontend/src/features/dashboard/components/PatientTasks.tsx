import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  Grid,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CloseIcon from "@mui/icons-material/Close";
import UploadFileIcon from "@mui/icons-material/UploadFile";

import { getJsonWithSession, postFormWithSession, postJsonWithSession } from "../../../shared/api/client";
import type { CareTask, ResponseReason } from "../../../shared/types/auth";

type Props = { sessionToken: string };

function dueLabel(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function statusLabel(value: CareTask["execution_status"]) {
  if (value === "completed_late") return "Done late";
  if (value === "completed") return "Done";
  if (value === "missed") return "Missed";
  return "To do";
}

export function PatientTasks({ sessionToken }: Props) {
  const [tasks, setTasks] = useState<CareTask[]>([]);
  const [reasons, setReasons] = useState<ResponseReason[]>([]);
  const [selectedReason, setSelectedReason] = useState<ResponseReason | null>(null);
  const [missedTask, setMissedTask] = useState<string | null>(null);
  const [measurements, setMeasurements] = useState<Record<string, string>>({});
  const [files, setFiles] = useState<Record<string, File | undefined>>({});
  const [workingTask, setWorkingTask] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);

  const load = useCallback(async () => {
    try {
      const result = await getJsonWithSession<{ tasks: CareTask[] }>("/me/tasks", sessionToken);
      if (mounted.current) setTasks(result.tasks);
    } catch (loadError) {
      if (mounted.current) setError(loadError instanceof Error ? loadError.message : "Tasks could not be loaded");
    }
  }, [sessionToken]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    getJsonWithSession<{ reasons: ResponseReason[] }>("/terminology/response-reasons", sessionToken)
      .then((result) => { if (mounted.current) setReasons(result.reasons); })
      .catch(() => { if (mounted.current) setReasons([]); });
  }, [sessionToken]);

  const pending = useMemo(() => tasks.filter((task) => task.execution_status === "pending"), [tasks]);
  const finished = useMemo(() => tasks.filter((task) => task.execution_status !== "pending"), [tasks]);

  async function respond(task: CareTask, responseStatus: "taken" | "missed" | "done" | "recorded") {
    if (responseStatus === "missed" && task.task_type === "medication" && !selectedReason) {
      setError("Please choose why it was missed.");
      return;
    }
    const measurementUnit = String(task.configuration.measurement_unit || "");
    const numericValue = measurements[task.task_id];
    if (responseStatus === "recorded" && (!numericValue || !Number.isFinite(Number(numericValue)))) {
      setError("Please enter the reading.");
      return;
    }
    setWorkingTask(task.task_id);
    setError(null);
    try {
      await postJsonWithSession(
        `/tasks/${task.task_id}/responses`,
        {
          response_status: responseStatus,
          reason: responseStatus === "missed" && selectedReason ? {
            concept_id: selectedReason.conceptId,
            term: selectedReason.term,
          } : null,
          numeric_value: responseStatus === "recorded" ? Number(numericValue) : null,
          measurement_unit: responseStatus === "recorded" ? measurementUnit : null,
        },
        sessionToken,
      );
      setNotice("Saved");
      setMissedTask(null);
      setSelectedReason(null);
      await load();
    } catch (responseError) {
      setError(responseError instanceof Error ? responseError.message : "Response could not be saved");
    } finally {
      setWorkingTask(null);
    }
  }

  async function upload(task: CareTask) {
    const file = files[task.task_id];
    if (!file) {
      setError("Choose a PDF or photo first.");
      return;
    }
    setWorkingTask(task.task_id);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", file);
      await postFormWithSession(`/tasks/${task.task_id}/upload`, form, sessionToken);
      setNotice("Report uploaded");
      await load();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Report could not be uploaded");
    } finally {
      setWorkingTask(null);
    }
  }

  function taskCard(task: CareTask, active: boolean) {
    const busy = workingTask === task.task_id;
    return (
      <Grid key={task.task_id} size={{ xs: 12, md: 6 }}>
        <Paper variant="outlined" sx={{ p: 2.5, height: "100%", borderColor: active ? "primary.light" : "divider" }}>
          <Stack spacing={2}>
            <Stack direction="row" justifyContent="space-between" gap={1}>
              <Box>
                <Typography variant="h3">{task.title}</Typography>
                <Typography color="text.secondary">{active ? `Due ${dueLabel(task.due_at)}` : statusLabel(task.execution_status)}</Typography>
              </Box>
              <Chip size="small" color={active ? "warning" : task.execution_status === "missed" ? "error" : "success"} label={statusLabel(task.execution_status)} />
            </Stack>

            {active && task.task_type === "medication" ? (
              <Stack spacing={1.5}>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                  <Button fullWidth size="large" variant="contained" color="success" startIcon={<CheckCircleIcon />} disabled={busy} onClick={() => void respond(task, "taken")}>Taken</Button>
                  <Button fullWidth size="large" variant="outlined" color="error" startIcon={<CloseIcon />} disabled={busy} onClick={() => setMissedTask(task.task_id)}>Missed</Button>
                </Stack>
                {missedTask === task.task_id ? (
                  <Stack spacing={1.5}>
                    <Autocomplete options={reasons} value={selectedReason} onChange={(_, value) => setSelectedReason(value)} getOptionLabel={(option) => option.term} renderInput={(params) => <TextField {...params} label="Why?" />} />
                    <Button variant="contained" color="error" disabled={busy} onClick={() => void respond(task, "missed")}>Save missed</Button>
                  </Stack>
                ) : null}
              </Stack>
            ) : null}

            {active && task.task_type === "measurement" ? (
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                <TextField fullWidth type="number" label={`Reading (${String(task.configuration.measurement_unit || "")})`} value={measurements[task.task_id] || ""} onChange={(event) => setMeasurements((current) => ({ ...current, [task.task_id]: event.target.value }))} inputProps={{ step: "any" }} />
                <Button size="large" variant="contained" disabled={busy} onClick={() => void respond(task, "recorded")}>Save</Button>
              </Stack>
            ) : null}

            {active && task.task_type === "recommendation" ? (
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
                <Button fullWidth size="large" variant="contained" color="success" startIcon={<CheckCircleIcon />} disabled={busy} onClick={() => void respond(task, "done")}>Done</Button>
                <Button fullWidth size="large" variant="outlined" color="error" disabled={busy} onClick={() => void respond(task, "missed")}>Missed</Button>
              </Stack>
            ) : null}

            {active && task.task_type === "investigation" ? (
              <Stack spacing={1.5}>
                <Button component="label" size="large" variant="outlined" startIcon={<UploadFileIcon />}>
                  {files[task.task_id]?.name || "Choose report"}
                  <input hidden type="file" accept="application/pdf,image/jpeg" onChange={(event) => setFiles((current) => ({ ...current, [task.task_id]: event.target.files?.[0] }))} />
                </Button>
                <Button size="large" variant="contained" disabled={busy || !files[task.task_id]} onClick={() => void upload(task)}>Upload</Button>
              </Stack>
            ) : null}
          </Stack>
        </Paper>
      </Grid>
    );
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="h2">My Tasks</Typography>
        <Typography color="text.secondary">What needs attention now.</Typography>
      </Stack>
      {error ? <Alert severity="error" onClose={() => setError(null)}>{error}</Alert> : null}
      {notice ? <Alert severity="success" onClose={() => setNotice(null)}>{notice}</Alert> : null}
      {pending.length === 0 ? <Alert severity="success">Nothing pending.</Alert> : <Grid container spacing={2}>{pending.map((task) => taskCard(task, true))}</Grid>}
      {finished.length ? (
        <Stack spacing={1.5}>
          <Typography variant="h3">Past</Typography>
          <Grid container spacing={2}>{finished.map((task) => taskCard(task, false))}</Grid>
        </Stack>
      ) : null}
    </Stack>
  );
}

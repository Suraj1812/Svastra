import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Autocomplete,
  Button,
  ButtonGroup,
  Chip,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import LocalHospitalOutlinedIcon from "@mui/icons-material/LocalHospitalOutlined";
import PublishOutlinedIcon from "@mui/icons-material/PublishOutlined";
import RemoveIcon from "@mui/icons-material/Remove";
import SearchIcon from "@mui/icons-material/Search";

import {
  getJsonWithSession,
  postJsonWithSession,
} from "../../../shared/api/client";
import type {
  AdvisorySummary,
  AdvisoryConfigurationOptions,
  AdvisoryOptionsResult,
  CarePlanSummary,
  ProviderTerm,
  RelationshipListResult,
} from "../../../shared/types/auth";

type Props = { sessionToken: string };
function tagLabel(tag: ProviderTerm["tag"]) {
  return tag.charAt(0).toUpperCase() + tag.slice(1);
}

function optionLabel(value: string) {
  if (value.toLowerCase() === "asap" || value.toLowerCase() === "stat") return value.toUpperCase();
  return value.toLowerCase().replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function NumberStepper({ label, value, onChange, min = 1, max = 365, step = 1 }: { label: string; value: string; onChange: (value: string) => void; min?: number; max?: number; step?: number }) {
  const numeric = Number(value);
  const update = (next: number) => onChange(String(Math.min(max, Math.max(min, next))));
  return (
    <Stack spacing={0.75}>
      <Typography variant="caption" color="text.secondary">{label}</Typography>
      <ButtonGroup fullWidth aria-label={label}>
        <Button aria-label={`Decrease ${label}`} onClick={() => update((Number.isFinite(numeric) ? numeric : min) - step)} disabled={numeric <= min}><RemoveIcon /></Button>
        <TextField
          value={value}
          onChange={(event) => onChange(event.target.value)}
          type="number"
          inputProps={{ min, max, step, 'aria-label': label, style: { textAlign: "center" } }}
          sx={{ "& .MuiOutlinedInput-notchedOutline": { borderRadius: 0 } }}
        />
        <Button aria-label={`Increase ${label}`} onClick={() => update((Number.isFinite(numeric) ? numeric : min) + step)} disabled={numeric >= max}><AddIcon /></Button>
      </ButtonGroup>
    </Stack>
  );
}

function AdvisoryCard({ advisory }: { advisory: AdvisorySummary }) {
  return (
    <Paper variant="outlined" sx={{ p: 2.25 }}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1.5}>
        <Stack spacing={0.5}>
          <Typography variant="h3">{advisory.term}</Typography>
          <Typography color="text.secondary">{tagLabel(advisory.tag)}</Typography>
        </Stack>
        <Chip color={advisory.status === "PUBLISHED" ? "success" : "warning"} label={optionLabel(advisory.status)} />
      </Stack>
      {advisory.allergy_warnings?.map((warning) => (
        <Alert key={`${warning.code}-${warning.allergen}`} severity="warning" sx={{ mt: 1.5 }}>
          {warning.message}. Choose another medicine.
        </Alert>
      ))}
      {advisory.status === "PUBLISHED" ? (
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.5 }}>
          <Chip size="small" color={advisory.execution_status === "pending" ? "info" : advisory.execution_status === "missed" ? "error" : "success"} variant="outlined" label={optionLabel(advisory.execution_status)} />
          <Chip size="small" variant="outlined" label={`Created ${formatDate(advisory.created_at)}`} />
          {advisory.published_at ? <Chip size="small" variant="outlined" label={`Published ${formatDate(advisory.published_at)}`} /> : null}
        </Stack>
      ) : <Chip size="small" variant="outlined" label={`Created ${formatDate(advisory.created_at)}`} sx={{ mt: 1.5 }} />}
    </Paper>
  );
}

export function CarePlanWorkspace({ sessionToken }: Props) {
  const [relationships, setRelationships] = useState<RelationshipListResult["relationships"]>([]);
  const [plans, setPlans] = useState<CarePlanSummary[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [creatingPlan, setCreatingPlan] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [patientId, setPatientId] = useState("");
  const [title, setTitle] = useState("");

  const [search, setSearch] = useState("");
  const [terms, setTerms] = useState<ProviderTerm[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedTerm, setSelectedTerm] = useState<ProviderTerm | null>(null);
  const [options, setOptions] = useState<AdvisoryConfigurationOptions | null>(null);
  const [frequency, setFrequency] = useState("once_daily");
  const [durationValue, setDurationValue] = useState("7");
  const [durationUnit, setDurationUnit] = useState("days");
  const [instructions, setInstructions] = useState("");
  const [doseValue, setDoseValue] = useState("");
  const [doseUnit, setDoseUnit] = useState("mg");
  const [route, setRoute] = useState("oral");
  const [measurementUnit, setMeasurementUnit] = useState("°C");
  const [priority, setPriority] = useState("routine");
  const [dueDate, setDueDate] = useState(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().slice(0, 10);
  });
  const [alertIfNotUploaded, setAlertIfNotUploaded] = useState(true);
  const [graceDays, setGraceDays] = useState("2");
  const [valueWarningEnabled, setValueWarningEnabled] = useState(false);
  const [warningCondition, setWarningCondition] = useState("more_than");
  const [warningThreshold, setWarningThreshold] = useState("");
  const [warningNotification, setWarningNotification] = useState("immediate");
  const [warningSeverity, setWarningSeverity] = useState("high");
  const [nonResponseEnabled, setNonResponseEnabled] = useState(false);
  const [clinicalGraceMinutes, setClinicalGraceMinutes] = useState("60");
  const [nonResponseNotification, setNonResponseNotification] = useState("immediate");
  const [allergyWarning, setAllergyWarning] = useState<string | null>(null);
  const [publishOpen, setPublishOpen] = useState(false);
  const optionRequest = useRef(0);
  const searchRequest = useRef(0);

  const activeRelationships = relationships.filter((item) => item.relationship_status === "ACTIVE");
  const selectedPlan = plans.find((plan) => plan.id === selectedPlanId) || null;
  const draftAdvisories = selectedPlan?.advisories.filter((item) => item.status === "DRAFT") || [];
  const publishedAdvisories = selectedPlan?.advisories.filter((item) => item.status === "PUBLISHED") || [];
  const planLabel = (plan: CarePlanSummary) => {
    const mobile = activeRelationships.find(
      (relationship) => relationship.patient.id === plan.patient.id,
    )?.mobile_number;
    return `${plan.title} — ${plan.patient.full_name}${mobile ? ` — ${mobile}` : ""}`;
  };

  const load = useCallback(async () => {
    setError(null);
    try {
      const [relationshipResult, planResult] = await Promise.all([
        getJsonWithSession<RelationshipListResult>("/relationships/patients?status=ACTIVE&include_mobile=true", sessionToken),
        getJsonWithSession<{ care_plans: CarePlanSummary[] }>("/care-plans", sessionToken),
      ]);
      setRelationships(relationshipResult.relationships);
      setPlans(planResult.care_plans);
      setSelectedPlanId((current) => current || planResult.care_plans[0]?.id || null);
      if (planResult.care_plans.length === 0) setCreatingPlan(true);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Care plans could not be loaded");
    }
  }, [sessionToken]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (search.trim().length < 3 || selectedTerm?.term === search) {
      searchRequest.current += 1;
      setTerms([]);
      return;
    }
    const requestId = ++searchRequest.current;
    const timer = window.setTimeout(async () => {
      setSearching(true);
      try {
        const result = await getJsonWithSession<{ terms: ProviderTerm[] }>(
          `/terminology/provider-terms?query=${encodeURIComponent(search.trim())}`,
          sessionToken,
        );
        if (requestId === searchRequest.current) setTerms(result.terms);
      } catch (searchError) {
        if (requestId === searchRequest.current) setError(searchError instanceof Error ? searchError.message : "Terminology search failed");
      } finally {
        if (requestId === searchRequest.current) setSearching(false);
      }
    }, 300);
    return () => window.clearTimeout(timer);
  }, [search, selectedTerm?.term, sessionToken]);

  async function createDraft() {
    if (!patientId || title.trim().length < 3) {
      setError("Select a linked patient and enter a care-plan title of at least 3 characters.");
      return;
    }
    setWorking(true);
    setError(null);
    try {
      const plan = await postJsonWithSession<CarePlanSummary>(
        "/care-plans",
        {
          patient_id: Number(patientId),
          title: title.trim(),
          diagnosis: null,
        },
        sessionToken,
      );
      setNotice("Care-plan draft created. Add a clinical advisory next.");
      setTitle("");
      await load();
      setSelectedPlanId(plan.id);
      setCreatingPlan(false);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Care plan could not be created");
    } finally {
      setWorking(false);
    }
  }

  async function selectTerm(term: ProviderTerm) {
    const requestId = ++optionRequest.current;
    setSelectedTerm(term);
    setSearch(term.term);
    setTerms([]);
    setOptions(null);
    setDoseValue("");
    setValueWarningEnabled(false);
    setWarningThreshold("");
    setNonResponseEnabled(false);
    try {
      const result = await getJsonWithSession<AdvisoryOptionsResult>(
        `/terminology/provider-terms/${encodeURIComponent(term.conceptId)}/advisory-options`,
        sessionToken,
      );
      if (requestId !== optionRequest.current) return;
      setOptions(result.options);
      setFrequency(result.options.frequencies[0]?.value || "once_daily");
      setDurationUnit(result.options.duration_units[1] || result.options.duration_units[0] || "days");
      setDoseUnit(result.options.dose_units?.[1] || result.options.dose_units?.[0] || "mg");
      setRoute(result.options.routes?.[0] || "oral");
      if (result.options.medication_details) setDoseValue("1");
      setMeasurementUnit(result.options.measurement_units?.[0] || "");
      setPriority(result.options.priorities?.[0] || "routine");
      setWarningCondition(result.options.comparators?.[0] || "more_than");
      setWarningNotification(result.options.notifications[0] || "immediate");
      setNonResponseNotification(result.options.notifications[0] || "immediate");
    } catch (optionsError) {
      if (requestId !== optionRequest.current) return;
      setSelectedTerm(null);
      setError(optionsError instanceof Error ? optionsError.message : "Advisory controls could not be loaded");
    }
  }

  const advisoryConfiguration = useMemo(() => {
    const common = {
      frequency,
      duration_value: Number(durationValue),
      duration_unit: durationUnit,
      additional_instructions: instructions.trim() || undefined,
      non_response_warning: nonResponseEnabled ? {
        clinical_grace_minutes: Number(clinicalGraceMinutes),
        notification: nonResponseNotification,
      } : undefined,
    };
    if (selectedTerm?.tag === "medication") return { ...common, dose_value: Number(doseValue), dose_unit: doseUnit, route };
    if (selectedTerm?.tag === "measurement") return {
      ...common,
      measurement_unit: measurementUnit,
      value_warning: valueWarningEnabled ? {
        condition: warningCondition,
        threshold_value: Number(warningThreshold),
        measurement_unit: measurementUnit,
        notification: warningNotification,
        severity: warningSeverity,
      } : undefined,
    };
    if (selectedTerm?.tag === "investigation") return {
      ...common,
      priority,
      due_date: dueDate,
      upload_required: true,
      alert_if_not_uploaded: alertIfNotUploaded,
      grace_period_value: Number(graceDays),
      grace_period_unit: "days",
    };
    return common;
  }, [alertIfNotUploaded, clinicalGraceMinutes, doseUnit, doseValue, dueDate, durationUnit, durationValue, frequency, graceDays, instructions, measurementUnit, nonResponseEnabled, nonResponseNotification, priority, route, selectedTerm?.tag, valueWarningEnabled, warningCondition, warningNotification, warningSeverity, warningThreshold]);

  async function addAdvisory() {
    if (!selectedPlan || !selectedTerm) {
      setError("Choose a draft and select an approved clinical term.");
      return;
    }
    if (!options) {
      setError("Approved advisory controls are still loading.");
      return;
    }
    if (!durationValue || Number(durationValue) < 1 || Number(durationValue) > 365 || !Number.isInteger(Number(durationValue))) {
      setError("Duration must be a whole number between 1 and 365.");
      return;
    }
    if (selectedTerm.tag === "medication" && (!doseValue || Number(doseValue) <= 0)) {
      setError("Enter a positive medication dose.");
      return;
    }
    if (selectedTerm.tag === "measurement" && !measurementUnit) {
      setError("Choose an approved measurement unit.");
      return;
    }
    if (selectedTerm.tag === "investigation" && (!dueDate || Number(graceDays) < 0 || Number(graceDays) > 30)) {
      setError("Choose a due date and a grace period from 0 to 30 days.");
      return;
    }
    if (valueWarningEnabled && (!warningThreshold || !Number.isFinite(Number(warningThreshold)))) {
      setError("Enter a valid threshold for the value warning.");
      return;
    }
    if (nonResponseEnabled && (!clinicalGraceMinutes || Number(clinicalGraceMinutes) < 1 || Number(clinicalGraceMinutes) > 1440)) {
      setError("Clinical grace period must be between 1 and 1440 minutes.");
      return;
    }
    setWorking(true);
    setError(null);
    try {
      const created = await postJsonWithSession<AdvisorySummary>(
        `/care-plans/${selectedPlan.id}/advisories`,
        {
          concept_id: selectedTerm.conceptId,
          term: selectedTerm.term,
          tag: selectedTerm.tag,
          configuration: advisoryConfiguration,
        },
        sessionToken,
      );
      setNotice(`${selectedTerm.term} added to the care plan.`);
      setAllergyWarning(created.allergy_warnings?.[0]?.message || null);
      setSelectedTerm(null);
      setSearch("");
      setInstructions("");
      await load();
    } catch (advisoryError) {
      setError(advisoryError instanceof Error ? advisoryError.message : "Advisory could not be added");
    } finally {
      setWorking(false);
    }
  }

  async function publish() {
    if (!selectedPlan) return;
    setWorking(true);
    setError(null);
    try {
      const result = await postJsonWithSession<CarePlanSummary>(
        `/care-plans/${selectedPlan.id}/publish`,
        { confirmed: true },
        sessionToken,
      );
      setPublishOpen(false);
      setNotice("Instructions sent to the patient.");
      await load();
    } catch (publishError) {
      setError(publishError instanceof Error ? publishError.message : "Care plan could not be published");
    } finally {
      setWorking(false);
    }
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="h2">Care Plans</Typography>
        <Typography color="text.secondary">
          Create and send care instructions.
        </Typography>
      </Stack>
      {error ? <Alert severity="error" onClose={() => setError(null)}>{error}</Alert> : null}
      {notice ? <Alert severity="success" onClose={() => setNotice(null)}>{notice}</Alert> : null}
      {allergyWarning ? <Alert severity="error" onClose={() => setAllergyWarning(null)}>{allergyWarning}. Choose another medicine.</Alert> : null}

      <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}>
        <Stack spacing={2.5}>
          <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ xs: "stretch", sm: "center" }} gap={1.5}>
            <Typography variant="h3">1. Care plan</Typography>
            {!creatingPlan ? <Button variant="outlined" startIcon={<AddCircleOutlineIcon />} onClick={() => setCreatingPlan(true)}>New care plan</Button> : null}
          </Stack>
          {activeRelationships.length === 0 ? (
            <Alert severity="warning">An active provider-patient relationship is required before authoring.</Alert>
          ) : creatingPlan ? (
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField select fullWidth label="Linked patient" value={patientId} onChange={(event) => setPatientId(event.target.value)}>
                  {activeRelationships.map((item) => (
                    <MenuItem key={item.id} value={item.patient.id}>
                      {item.patient.full_name}{item.mobile_number ? ` — ${item.mobile_number}` : ""}
                    </MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField fullWidth label="Care plan name" value={title} onChange={(event) => setTitle(event.target.value)} inputProps={{ maxLength: 160 }} />
              </Grid>
            </Grid>
          ) : (
            <Autocomplete
              options={plans}
              value={selectedPlan}
              onChange={(_, plan) => setSelectedPlanId(plan?.id ?? null)}
              getOptionLabel={planLabel}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              renderInput={(params) => <TextField {...params} label="Search or select care plan" />}
            />
          )}
          {creatingPlan ? (
            <Stack direction="row" spacing={1}>
              <Button variant="contained" startIcon={<AddCircleOutlineIcon />} onClick={createDraft} disabled={working || activeRelationships.length === 0}>Create</Button>
              {plans.length > 0 ? <Button onClick={() => { setCreatingPlan(false); setPatientId(""); setTitle(""); }}>Cancel</Button> : null}
            </Stack>
          ) : null}
        </Stack>
      </Paper>

      {!creatingPlan && selectedPlan && selectedPlan.status !== "INACTIVE" ? (
        <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}>
          <Stack spacing={2.5}>
            <Typography variant="h3">2. Add advice</Typography>
            <Typography color="text.secondary">{selectedPlan.title} · {selectedPlan.patient.full_name}</Typography>
            <TextField
              label="Search clinical term"
              value={search}
              onChange={(event) => { optionRequest.current += 1; setSearch(event.target.value); setSelectedTerm(null); setOptions(null); }}
              helperText={searching ? "Searching approved terminology…" : "Type at least 3 characters"}
              InputProps={{ startAdornment: <SearchIcon color="action" sx={{ mr: 1 }} /> }}
            />
            {terms.length > 0 ? (
              <Paper variant="outlined">
                {terms.map((term) => (
                  <Button key={term.conceptId} fullWidth onClick={() => void selectTerm(term)} sx={{ justifyContent: "space-between", px: 2, py: 1.5 }}>
                    <span>{term.term}</span><Chip size="small" label={tagLabel(term.tag)} />
                  </Button>
                ))}
              </Paper>
            ) : null}

            {selectedTerm && options ? (
              <Stack spacing={2.5}>
                <Alert icon={<LocalHospitalOutlinedIcon />} severity="success">{selectedTerm.term} · {tagLabel(selectedTerm.tag)}</Alert>
                {options.medication_details ? (
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Grid container spacing={2}>
                      <Grid size={{ xs: 6, md: 3 }}><Typography variant="caption" color="text.secondary">Form</Typography><Typography>{options.medication_details.dose_form}</Typography></Grid>
                      <Grid size={{ xs: 6, md: 3 }}><Typography variant="caption" color="text.secondary">Route</Typography><Typography>{options.medication_details.route}</Typography></Grid>
                      <Grid size={{ xs: 6, md: 3 }}><Typography variant="caption" color="text.secondary">How to take</Typography><Typography>{options.medication_details.method}</Typography></Grid>
                      <Grid size={{ xs: 6, md: 3 }}><Typography variant="caption" color="text.secondary">Strength</Typography><Typography>{options.medication_details.strength}</Typography></Grid>
                    </Grid>
                  </Paper>
                ) : null}
                <Grid container spacing={2}>
                  {selectedTerm.tag === "medication" ? (
                    <>
                      <Grid size={{ xs: 12, md: 4 }}><NumberStepper label="Dose quantity" value={doseValue} onChange={setDoseValue} min={0.001} max={1000000} step={1} /></Grid>
                      {!options.medication_details ? <Grid size={{ xs: 6, md: 4 }}><TextField select fullWidth label="Dose unit" value={doseUnit} onChange={(event) => setDoseUnit(event.target.value)}>{options.dose_units?.map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}</TextField></Grid> : null}
                      {!options.medication_details ? <Grid size={{ xs: 6, md: 4 }}><TextField select fullWidth label="Route" value={route} onChange={(event) => setRoute(event.target.value)}>{options.routes?.map((item) => <MenuItem key={item} value={item}>{optionLabel(item)}</MenuItem>)}</TextField></Grid> : null}
                    </>
                  ) : null}
                  {selectedTerm.tag === "measurement" ? (
                    <Grid size={{ xs: 12, md: 4 }}><TextField select fullWidth label="Measurement unit" value={measurementUnit} onChange={(event) => setMeasurementUnit(event.target.value)}>{options.measurement_units?.map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}</TextField></Grid>
                  ) : null}
                  {selectedTerm.tag === "investigation" ? (
                    <>
                      <Grid size={{ xs: 12 }}>
                        <Stack spacing={0.75}>
                          <Typography variant="caption" color="text.secondary">Priority</Typography>
                          <ToggleButtonGroup exclusive value={priority} onChange={(_, value) => value && setPriority(value)} aria-label="Priority" sx={{ flexWrap: "wrap" }}>
                            {options.priorities?.map((item) => <ToggleButton key={item} value={item}>{optionLabel(item)}</ToggleButton>)}
                          </ToggleButtonGroup>
                        </Stack>
                      </Grid>
                      <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth type="date" label="Report due" value={dueDate} onChange={(event) => setDueDate(event.target.value)} slotProps={{ inputLabel: { shrink: true } }} /></Grid>
                      <Grid size={{ xs: 12, md: 4 }}><NumberStepper label="Grace period (days)" value={graceDays} onChange={setGraceDays} min={0} max={30} /></Grid>
                      <Grid size={{ xs: 12 }}><FormControlLabel control={<Switch checked disabled />} label="Report upload required" /></Grid>
                      <Grid size={{ xs: 12 }}><FormControlLabel control={<Checkbox checked={alertIfNotUploaded} onChange={(event) => setAlertIfNotUploaded(event.target.checked)} />} label="Alert me if no report" /></Grid>
                    </>
                  ) : null}
                  <Grid size={{ xs: 12, md: 4 }}>
                    <Autocomplete
                      disableClearable
                      options={options.frequencies}
                      value={options.frequencies.find((item) => item.value === frequency) || options.frequencies[0]}
                      onChange={(_, item) => setFrequency(item.value)}
                      getOptionLabel={(item) => item.label}
                      isOptionEqualToValue={(option, value) => option.value === value.value}
                      renderInput={(params) => <TextField {...params} label="Frequency" />}
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 3 }}><NumberStepper label="Duration" value={durationValue} onChange={setDurationValue} min={1} max={365} /></Grid>
                  <Grid size={{ xs: 6, md: 2 }}><TextField select fullWidth label="Duration unit" value={durationUnit} onChange={(event) => setDurationUnit(event.target.value)}>{options.duration_units.map((unit) => <MenuItem key={unit} value={unit}>{unit}</MenuItem>)}</TextField></Grid>
                  {selectedTerm.tag !== "measurement" ? <Grid size={{ xs: 12 }}>
                    <Autocomplete
                      freeSolo
                      options={options.instruction_suggestions || []}
                      value={instructions}
                      onInputChange={(_, value) => setInstructions(value.slice(0, 500))}
                      renderInput={(params) => <TextField {...params} label={selectedTerm.tag === "recommendation" ? "Instruction" : "Additional instruction (optional)"} />}
                    />
                  </Grid> : null}
                  {selectedTerm.tag === "measurement" ? (
                    <Grid size={{ xs: 12 }}>
                      <Stack spacing={1.5}>
                        <FormControlLabel control={<Checkbox checked={valueWarningEnabled} onChange={(event) => setValueWarningEnabled(event.target.checked)} />} label="Add an optional value warning" />
                        {valueWarningEnabled ? (
                          <Grid container spacing={2}>
                            <Grid size={{ xs: 12, md: 4 }}><TextField select fullWidth label="Warn when value is" value={warningCondition} onChange={(event) => setWarningCondition(event.target.value)}>{options.comparators?.map((item) => <MenuItem key={item} value={item}>{optionLabel(item)}</MenuItem>)}</TextField></Grid>
                            <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth type="number" label={`Threshold (${measurementUnit})`} value={warningThreshold} onChange={(event) => setWarningThreshold(event.target.value)} inputProps={{ step: "any" }} /></Grid>
                            <Grid size={{ xs: 12, md: 4 }}><TextField select fullWidth label="Severity" value={warningSeverity} onChange={(event) => setWarningSeverity(event.target.value)}>{["low", "medium", "high", "critical"].map((item) => <MenuItem key={item} value={item}>{optionLabel(item)}</MenuItem>)}</TextField></Grid>
                          </Grid>
                        ) : null}
                      </Stack>
                    </Grid>
                  ) : null}
                  {selectedTerm.tag === "measurement" ? <Grid size={{ xs: 12 }}>
                    <Stack spacing={1.5}>
                      <FormControlLabel control={<Checkbox checked={nonResponseEnabled} onChange={(event) => setNonResponseEnabled(event.target.checked)} />} label="Alert me if there is no response" />
                      {nonResponseEnabled ? (
                        <Grid container spacing={2}>
                          <Grid size={{ xs: 12, md: 4 }}><TextField fullWidth type="number" label="Clinical grace period (minutes)" value={clinicalGraceMinutes} onChange={(event) => setClinicalGraceMinutes(event.target.value)} inputProps={{ min: 1, max: 1440 }} /></Grid>
                        </Grid>
                      ) : null}
                    </Stack>
                  </Grid> : null}
                </Grid>
                <Button variant="contained" startIcon={<AddCircleOutlineIcon />} onClick={addAdvisory} disabled={working} sx={{ alignSelf: "flex-start" }}>Add Advisory</Button>
              </Stack>
            ) : selectedTerm ? <Alert severity="info">Loading approved controls…</Alert> : null}
          </Stack>
        </Paper>
      ) : null}

      {!creatingPlan && selectedPlan ? (
        <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}>
          <Stack spacing={2}>
            <Typography variant="h3">3. Advisories</Typography>
            {selectedPlan.advisories.length === 0 ? <Alert severity="info">Add at least one instruction.</Alert> : null}
            {draftAdvisories.length > 0 ? (
              <Stack spacing={1.5}>
                <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1.5}>
                  <Typography variant="h4">Ready to send</Typography>
                  {selectedPlan.status !== "INACTIVE" ? <Button variant="contained" color="success" startIcon={<PublishOutlinedIcon />} onClick={() => setPublishOpen(true)} disabled={draftAdvisories.some((item) => item.allergy_warnings.length > 0)}>Send care plan</Button> : null}
                </Stack>
                {draftAdvisories.map((advisory) => <AdvisoryCard key={advisory.id} advisory={advisory} />)}
              </Stack>
            ) : null}
            {publishedAdvisories.length > 0 ? (
              <Stack spacing={1.5}>
                <Typography variant="h4">Published advisories</Typography>
                {publishedAdvisories.map((advisory) => <AdvisoryCard key={advisory.id} advisory={advisory} />)}
              </Stack>
            ) : null}
          </Stack>
        </Paper>
      ) : null}

      <Dialog open={publishOpen} onClose={() => setPublishOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Send these instructions?</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <Alert severity="warning">Please check them once. Sent instructions cannot be edited.</Alert>
            <Typography>{selectedPlan?.title}</Typography>
            <Typography color="text.secondary">{selectedPlan?.advisories.length || 0} instructions</Typography>
          </Stack>
        </DialogContent>
        <DialogActions><Button onClick={() => setPublishOpen(false)} disabled={working}>Cancel</Button><Button variant="contained" color="success" onClick={publish} disabled={working}>Send</Button></DialogActions>
      </Dialog>

    </Stack>
  );
}

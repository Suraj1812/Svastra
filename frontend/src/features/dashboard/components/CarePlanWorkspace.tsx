import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddCircleOutlineIcon from "@mui/icons-material/AddCircleOutline";
import LocalHospitalOutlinedIcon from "@mui/icons-material/LocalHospitalOutlined";
import PublishOutlinedIcon from "@mui/icons-material/PublishOutlined";
import SearchIcon from "@mui/icons-material/Search";

import {
  getJsonWithSession,
  postJsonWithSession,
} from "../../../shared/api/client";
import type {
  AdvisorySummary,
  CarePlanSummary,
  ProviderTerm,
  RelationshipListResult,
} from "../../../shared/types/auth";

type Props = { sessionToken: string };
type Frequency =
  | "once_daily"
  | "twice_daily"
  | "three_times_daily"
  | "four_times_daily"
  | "every_4_hours"
  | "every_6_hours"
  | "weekly"
  | "monthly"
  | "as_needed";

const frequencies: Array<{ value: Frequency; label: string }> = [
  { value: "once_daily", label: "Once daily" },
  { value: "twice_daily", label: "Twice daily" },
  { value: "three_times_daily", label: "Three times daily" },
  { value: "four_times_daily", label: "Four times daily" },
  { value: "every_4_hours", label: "Every 4 hours" },
  { value: "every_6_hours", label: "Every 6 hours" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
  { value: "as_needed", label: "As needed" },
];

function tagLabel(tag: ProviderTerm["tag"]) {
  return tag.charAt(0).toUpperCase() + tag.slice(1);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function AdvisoryCard({ advisory, publishing, onPublish }: { advisory: AdvisorySummary; publishing: boolean; onPublish: () => void }) {
  return (
    <Paper variant="outlined" sx={{ p: 2.25 }}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1.5}>
        <Stack spacing={0.5}>
          <Typography variant="h3">{advisory.term}</Typography>
          <Typography color="text.secondary">{tagLabel(advisory.tag)} advisory</Typography>
        </Stack>
        <Chip color={advisory.status === "PUBLISHED" ? "success" : "warning"} label={advisory.status} />
      </Stack>
      {advisory.allergy_warnings?.map((warning) => (
        <Alert key={`${warning.code}-${warning.allergen}`} severity="warning" sx={{ mt: 1.5 }}>
          {warning.message}. This MVP warning is non-blocking and requires provider review.
        </Alert>
      ))}
      {advisory.status === "DRAFT" ? (
        <Button size="small" variant="contained" startIcon={<PublishOutlinedIcon />} onClick={onPublish} disabled={publishing} sx={{ mt: 1.5 }}>
          Publish Advisory
        </Button>
      ) : null}
    </Paper>
  );
}

export function CarePlanWorkspace({ sessionToken }: Props) {
  const [relationships, setRelationships] = useState<RelationshipListResult["relationships"]>([]);
  const [plans, setPlans] = useState<CarePlanSummary[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [patientId, setPatientId] = useState("");
  const [title, setTitle] = useState("");
  const [diagnosis, setDiagnosis] = useState("");

  const [search, setSearch] = useState("");
  const [terms, setTerms] = useState<ProviderTerm[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedTerm, setSelectedTerm] = useState<ProviderTerm | null>(null);
  const [frequency, setFrequency] = useState<Frequency>("once_daily");
  const [durationValue, setDurationValue] = useState("7");
  const [durationUnit, setDurationUnit] = useState("days");
  const [instructions, setInstructions] = useState("");
  const [dose, setDose] = useState("");
  const [route, setRoute] = useState("oral");
  const [measurementUnit, setMeasurementUnit] = useState("°C");
  const [targetValue, setTargetValue] = useState("");
  const [priority, setPriority] = useState("routine");
  const [recommendationInstruction, setRecommendationInstruction] = useState("");
  const [allergyWarning, setAllergyWarning] = useState<string | null>(null);
  const [publishOpen, setPublishOpen] = useState(false);
  const [publishAdvisoryTarget, setPublishAdvisoryTarget] = useState<AdvisorySummary | null>(null);

  const activeRelationships = relationships.filter((item) => item.relationship_status === "ACTIVE");
  const selectedPlan = plans.find((plan) => plan.id === selectedPlanId) || null;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [relationshipResult, planResult] = await Promise.all([
        getJsonWithSession<RelationshipListResult>("/relationships/patients?status=ACTIVE", sessionToken),
        getJsonWithSession<{ care_plans: CarePlanSummary[] }>("/care-plans", sessionToken),
      ]);
      setRelationships(relationshipResult.relationships);
      setPlans(planResult.care_plans);
      setSelectedPlanId((current) => current || planResult.care_plans[0]?.id || null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Care plans could not be loaded");
    } finally {
      setLoading(false);
    }
  }, [sessionToken]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (search.trim().length < 3 || selectedTerm?.term === search) {
      setTerms([]);
      return;
    }
    const timer = window.setTimeout(async () => {
      setSearching(true);
      try {
        const result = await getJsonWithSession<{ terms: ProviderTerm[] }>(
          `/terminology/provider-terms?query=${encodeURIComponent(search.trim())}`,
          sessionToken,
        );
        setTerms(result.terms);
      } catch (searchError) {
        setError(searchError instanceof Error ? searchError.message : "Terminology search failed");
      } finally {
        setSearching(false);
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
          diagnosis: diagnosis.trim() || null,
        },
        sessionToken,
      );
      setNotice("Care-plan draft created. Add a clinical advisory next.");
      setTitle("");
      setDiagnosis("");
      await load();
      setSelectedPlanId(plan.id);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Care plan could not be created");
    } finally {
      setWorking(false);
    }
  }

  function selectTerm(term: ProviderTerm) {
    setSelectedTerm(term);
    setSearch(term.term);
    setTerms([]);
    setDose("");
    setRoute("oral");
    setMeasurementUnit(term.conceptId === "demo_term_blood_pressure" ? "mmHg" : "°C");
    setTargetValue("");
    setPriority("routine");
    setRecommendationInstruction("");
  }

  const advisoryConfiguration = useMemo(() => {
    const common = {
      frequency,
      duration_value: Number(durationValue),
      duration_unit: durationUnit,
      additional_instructions: instructions.trim() || undefined,
    };
    if (selectedTerm?.tag === "medication") return { ...common, dose: dose.trim(), route };
    if (selectedTerm?.tag === "measurement") return { ...common, measurement_unit: measurementUnit, target_value: targetValue.trim() };
    if (selectedTerm?.tag === "investigation") return { ...common, priority, attachment_required: true };
    return { ...common, instruction: recommendationInstruction.trim() };
  }, [dose, durationUnit, durationValue, frequency, instructions, measurementUnit, priority, recommendationInstruction, route, selectedTerm?.tag, targetValue]);

  async function addAdvisory() {
    if (!selectedPlan || !selectedTerm) {
      setError("Choose a draft and select an approved clinical term.");
      return;
    }
    if (selectedTerm.tag === "medication" && !dose.trim()) {
      setError("Dose is required for medication advisories.");
      return;
    }
    if (selectedTerm.tag === "measurement" && !targetValue.trim()) {
      setError("Target value is required for measurement advisories.");
      return;
    }
    if (selectedTerm.tag === "recommendation" && !recommendationInstruction.trim()) {
      setError("Instruction is required for recommendation advisories.");
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
      setNotice(`Care plan published. PostOffice event ${result.event_id} was delivered and acknowledged.`);
      await load();
    } catch (publishError) {
      setError(publishError instanceof Error ? publishError.message : "Care plan could not be published");
    } finally {
      setWorking(false);
    }
  }

  async function publishOne(advisoryId: number) {
    if (!selectedPlan) return;
    setWorking(true);
    setError(null);
    try {
      const result = await postJsonWithSession<{ advisory: AdvisorySummary; event_id: string; acknowledgement: { ack_id: string } }>(
        `/care-plans/${selectedPlan.id}/advisories/${advisoryId}/publish`,
        { confirmed: true },
        sessionToken,
      );
      setPublishAdvisoryTarget(null);
      setNotice(`Advisory published and acknowledged (${result.acknowledgement.ack_id}).`);
      await load();
    } catch (publishError) {
      setError(publishError instanceof Error ? publishError.message : "Advisory could not be published");
    } finally {
      setWorking(false);
    }
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="h2">Care Plan Builder</Typography>
        <Typography color="text.secondary">
          Author validated instructions for consent-backed linked patients using approved clinical terminology.
        </Typography>
      </Stack>
      {error ? <Alert severity="error" onClose={() => setError(null)}>{error}</Alert> : null}
      {notice ? <Alert severity="success" onClose={() => setNotice(null)}>{notice}</Alert> : null}
      {allergyWarning ? <Alert severity="warning" onClose={() => setAllergyWarning(null)}>{allergyWarning}. Review before publishing.</Alert> : null}

      <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}>
        <Stack spacing={2.5}>
          <Typography variant="h3">1. Clinical context</Typography>
          {activeRelationships.length === 0 ? (
            <Alert severity="warning">An active provider-patient relationship is required before authoring.</Alert>
          ) : (
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 4 }}>
                <TextField select fullWidth label="Linked patient" value={patientId} onChange={(event) => setPatientId(event.target.value)}>
                  {activeRelationships.map((item) => (
                    <MenuItem key={item.id} value={item.patient.id}>{item.patient.full_name}</MenuItem>
                  ))}
                </TextField>
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <TextField fullWidth label="Care-plan title" value={title} onChange={(event) => setTitle(event.target.value)} inputProps={{ maxLength: 160 }} />
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <TextField fullWidth label="Diagnosis / clinical context" value={diagnosis} onChange={(event) => setDiagnosis(event.target.value)} inputProps={{ maxLength: 255 }} />
              </Grid>
            </Grid>
          )}
          <Button variant="contained" startIcon={<AddCircleOutlineIcon />} onClick={createDraft} disabled={working || activeRelationships.length === 0} sx={{ alignSelf: "flex-start" }}>
            Create Draft
          </Button>
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ overflow: "hidden" }}>
        <Box sx={{ p: { xs: 2, md: 3 } }}>
          <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={2}>
            <Stack spacing={0.5}>
              <Typography variant="h3">2. Select a care-plan draft</Typography>
              <Typography color="text.secondary">Published plans remain visible and cannot be silently edited.</Typography>
            </Stack>
            <TextField
              select
              label="Care plan"
              value={selectedPlanId || ""}
              onChange={(event) => setSelectedPlanId(Number(event.target.value))}
              sx={{ minWidth: { sm: 300 } }}
              disabled={loading || plans.length === 0}
            >
              {plans.map((plan) => (
                <MenuItem key={plan.id} value={plan.id}>{plan.title} — {plan.patient.full_name}</MenuItem>
              ))}
            </TextField>
          </Stack>
        </Box>
        {selectedPlan ? (
          <>
            <Divider />
            <Box sx={{ p: { xs: 2, md: 3 } }}>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 4 }}><Typography variant="caption" color="text.secondary">Patient</Typography><Typography>{selectedPlan.patient.full_name}</Typography></Grid>
                <Grid size={{ xs: 12, sm: 4 }}><Typography variant="caption" color="text.secondary">Diagnosis</Typography><Typography>{selectedPlan.diagnosis || "Not specified"}</Typography></Grid>
                <Grid size={{ xs: 12, sm: 4 }}><Typography variant="caption" color="text.secondary">Status</Typography><Box><Chip size="small" color={selectedPlan.status === "ACTIVE" ? "success" : "warning"} label={selectedPlan.status} /></Box></Grid>
              </Grid>
            </Box>
          </>
        ) : null}
      </Paper>

      {selectedPlan && selectedPlan.status !== "INACTIVE" ? (
        <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}>
          <Stack spacing={2.5}>
            <Typography variant="h3">3. Search and configure an advisory</Typography>
            <TextField
              label="Search clinical term"
              value={search}
              onChange={(event) => { setSearch(event.target.value); setSelectedTerm(null); }}
              helperText={searching ? "Searching approved terminology…" : "Type at least 3 characters"}
              InputProps={{ startAdornment: <SearchIcon color="action" sx={{ mr: 1 }} /> }}
            />
            {terms.length > 0 ? (
              <Paper variant="outlined">
                {terms.map((term) => (
                  <Button key={term.conceptId} fullWidth onClick={() => selectTerm(term)} sx={{ justifyContent: "space-between", px: 2, py: 1.5 }}>
                    <Stack alignItems="flex-start"><span>{term.term}</span><Typography variant="caption" color="text.secondary">ConceptId: {term.conceptId}</Typography></Stack><Chip size="small" label={tagLabel(term.tag)} />
                  </Button>
                ))}
              </Paper>
            ) : null}

            {selectedTerm ? (
              <Stack spacing={2.5}>
                <Alert icon={<LocalHospitalOutlinedIcon />} severity="success">
                  {selectedTerm.term} selected. {tagLabel(selectedTerm.tag)} controls loaded.
                </Alert>
                <Grid container spacing={2}>
                  {selectedTerm.tag === "medication" ? (
                    <><Grid size={{ xs: 12, md: 3 }}><TextField fullWidth label="Dose" value={dose} onChange={(event) => setDose(event.target.value)} placeholder="e.g. 650 mg" /></Grid><Grid size={{ xs: 12, md: 3 }}><TextField select fullWidth label="Route" value={route} onChange={(event) => setRoute(event.target.value)}>{["oral", "topical", "inhaled", "injection", "other"].map((item) => <MenuItem key={item} value={item}>{item}</MenuItem>)}</TextField></Grid></>
                  ) : null}
                  {selectedTerm.tag === "measurement" ? (
                    <><Grid size={{ xs: 12, md: 3 }}><TextField fullWidth label="Target value" value={targetValue} onChange={(event) => setTargetValue(event.target.value)} placeholder="e.g. 98.6" /></Grid><Grid size={{ xs: 12, md: 3 }}><TextField select fullWidth label="Measurement unit" value={measurementUnit} onChange={(event) => setMeasurementUnit(event.target.value)}><MenuItem value="°C">°C</MenuItem><MenuItem value="°F">°F</MenuItem><MenuItem value="mmHg">mmHg</MenuItem></TextField></Grid></>
                  ) : null}
                  {selectedTerm.tag === "investigation" ? (
                    <Grid size={{ xs: 12, md: 4 }}><TextField select fullWidth label="Priority" value={priority} onChange={(event) => setPriority(event.target.value)}><MenuItem value="routine">Routine</MenuItem><MenuItem value="urgent">Urgent</MenuItem><MenuItem value="stat">Stat</MenuItem></TextField></Grid>
                  ) : null}
                  {selectedTerm.tag === "recommendation" ? (
                    <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Instruction" value={recommendationInstruction} onChange={(event) => setRecommendationInstruction(event.target.value)} placeholder="e.g. Walk for 20 minutes after breakfast" /></Grid>
                  ) : null}
                  <Grid size={{ xs: 12, md: 4 }}><TextField select fullWidth label="Frequency" value={frequency} onChange={(event) => setFrequency(event.target.value as Frequency)}>{frequencies.map((item) => <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>)}</TextField></Grid>
                  <Grid size={{ xs: 6, md: 2 }}><TextField fullWidth type="number" label="Duration" value={durationValue} onChange={(event) => setDurationValue(event.target.value)} inputProps={{ min: 1, max: 365 }} /></Grid>
                  <Grid size={{ xs: 6, md: 2 }}><TextField select fullWidth label="Unit" value={durationUnit} onChange={(event) => setDurationUnit(event.target.value)}>{["hours", "days", "weeks", "months"].map((unit) => <MenuItem key={unit} value={unit}>{unit}</MenuItem>)}</TextField></Grid>
                  <Grid size={{ xs: 12 }}><TextField fullWidth multiline minRows={2} label="Additional instructions (optional)" value={instructions} onChange={(event) => setInstructions(event.target.value)} inputProps={{ maxLength: 500 }} /></Grid>
                </Grid>
                <Button variant="contained" startIcon={<AddCircleOutlineIcon />} onClick={addAdvisory} disabled={working} sx={{ alignSelf: "flex-start" }}>Add Advisory</Button>
              </Stack>
            ) : null}
          </Stack>
        </Paper>
      ) : null}

      {selectedPlan ? (
        <Paper variant="outlined" sx={{ p: { xs: 2, md: 3 } }}>
          <Stack spacing={2}>
            <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1.5}>
              <Stack><Typography variant="h3">4. Review and publish</Typography><Typography color="text.secondary">Created {formatDate(selectedPlan.created_at)}</Typography></Stack>
              {selectedPlan.status !== "INACTIVE" && selectedPlan.advisories.some((item) => item.status === "DRAFT") ? <Button variant="contained" color="success" startIcon={<PublishOutlinedIcon />} onClick={() => setPublishOpen(true)}>Publish All Draft Advisories</Button> : null}
            </Stack>
            {selectedPlan.advisories.length === 0 ? <Alert severity="info">Add at least one advisory before publishing.</Alert> : selectedPlan.advisories.map((advisory) => <AdvisoryCard key={advisory.id} advisory={advisory} publishing={working} onPublish={() => setPublishAdvisoryTarget(advisory)} />)}
          </Stack>
        </Paper>
      ) : null}

      <Dialog open={publishOpen} onClose={() => setPublishOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Publish care plan?</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <Alert severity="warning">Publishing is immutable. Corrections must become new clinical events.</Alert>
            <Typography>{selectedPlan?.title}</Typography>
            <Typography color="text.secondary">{selectedPlan?.advisories.length || 0} validated advisories will be sent through PostOffice.</Typography>
          </Stack>
        </DialogContent>
        <DialogActions><Button onClick={() => setPublishOpen(false)} disabled={working}>Cancel</Button><Button variant="contained" color="success" onClick={publish} disabled={working}>Confirm Publish</Button></DialogActions>
      </Dialog>

      <Dialog open={Boolean(publishAdvisoryTarget)} onClose={() => setPublishAdvisoryTarget(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Publish this advisory?</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <Alert severity="warning">Publishing is immutable. Review the clinical instruction before it is delivered to the patient.</Alert>
            <Typography>{publishAdvisoryTarget?.term}</Typography>
            <Typography color="text.secondary">PostOffice will deliver the advisory and record the patient-side acknowledgement.</Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPublishAdvisoryTarget(null)} disabled={working}>Cancel</Button>
          <Button
            variant="contained"
            color="success"
            onClick={() => publishAdvisoryTarget && publishOne(publishAdvisoryTarget.id)}
            disabled={working}
          >
            Confirm Publish
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}

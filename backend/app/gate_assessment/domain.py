from dataclasses import dataclass
from enum import StrEnum


class GateCode(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


class GateAssessmentState(StrEnum):
    UNPROVEN = "UNPROVEN"
    PASS = "PASS"
    AT_RISK = "AT_RISK"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    PASS_CONFIRMED = "PASS_CONFIRMED"
    FAIL = "FAIL"
    REMEDIATION = "REMEDIATION"
    REASSESSMENT = "REASSESSMENT"


def gate_transition_allowed(current: str, target: str) -> bool:
    transitions = {
        GateAssessmentState.UNPROVEN.value: {
            GateAssessmentState.PASS.value,
        },
        GateAssessmentState.PASS.value: {
            GateAssessmentState.AT_RISK.value,
        },
        GateAssessmentState.AT_RISK.value: {
            GateAssessmentState.REVIEW_REQUIRED.value,
        },
        GateAssessmentState.REVIEW_REQUIRED.value: {
            GateAssessmentState.PASS_CONFIRMED.value,
            GateAssessmentState.FAIL.value,
        },
        GateAssessmentState.PASS_CONFIRMED.value: {
            GateAssessmentState.AT_RISK.value,
        },
        GateAssessmentState.FAIL.value: {
            GateAssessmentState.REMEDIATION.value,
        },
        GateAssessmentState.REMEDIATION.value: {
            GateAssessmentState.REASSESSMENT.value,
        },
        GateAssessmentState.REASSESSMENT.value: {
            GateAssessmentState.PASS.value,
            GateAssessmentState.FAIL.value,
        },
    }
    return target in transitions.get(current, set())


@dataclass(frozen=True)
class GateDefinitionSpec:
    code: GateCode
    name: str
    decision_question: str
    requirements: tuple[str, ...]
    outcomes: tuple[str, ...]


GATE_DEFINITION_REGISTRY: tuple[GateDefinitionSpec, ...] = (
    GateDefinitionSpec(
        code=GateCode.A,
        name="Foundation Readiness",
        decision_question="آیا فرد آماده ورود جدی به Product Core است؟",
        requirements=(
            "Trustworthiness = PASS",
            "Ownership = PASS",
            "Accountability = PASS",
            "Problem Framing حداقل Demonstrated",
            "Decision Making حداقل Demonstrated",
            "Data Thinking حداقل Demonstrated",
            "Reflection فعال",
        ),
        outcomes=(
            "ENTER PRODUCT CORE",
            "NOT YET",
        ),
    ),
    GateDefinitionSpec(
        code=GateCode.B,
        name="Product Judgment Readiness",
        decision_question=(
            "آیا فرد می‌تواند در مسئله محصولی پیچیده Judgment نشان دهد؟"
        ),
        requirements=(
            "Customer Understanding حداقل Demonstrated",
            "Product Discovery حداقل Demonstrated",
            "Metrics & Experimentation حداقل Demonstrated",
            "Decision Making در چند Context",
            "Replay معتبر",
        ),
        outcomes=(
            "ENTER INTEGRATED SIMULATION",
            "NOT YET",
        ),
    ),
    GateDefinitionSpec(
        code=GateCode.C,
        name="Real Project Readiness",
        decision_question=(
            "آیا امن است بخشی از واقعیت کسب‌وکار را به او بسپاریم؟"
        ),
        requirements=(
            "Gates رفتاری PASS",
            "Integrated Simulation",
            "Delivery حداقل Demonstrated",
            "Stakeholder Alignment حداقل Demonstrated",
            "Product Judgment قابل اتکا",
            "Behaviour Change اثبات‌شده",
        ),
        outcomes=(
            "ENTER APPRENTICESHIP",
            "NOT YET",
        ),
    ),
    GateDefinitionSpec(
        code=GateCode.D,
        name="Ownership Trial Readiness",
        decision_question="آیا می‌توان Outcome واقعی را به او سپرد؟",
        requirements=(
            "Evidence واقعی از Delivery",
            "Evidence واقعی از Stakeholder Alignment",
            "Accountability معتبر",
            "Strategy / Prioritization متناسب با Scope",
            "Real Project Evidence کافی",
        ),
        outcomes=(
            "GRANT OUTCOME OWNERSHIP",
            "REMEDIATE",
        ),
    ),
    GateDefinitionSpec(
        code=GateCode.E,
        name="Flag Board",
        decision_question=(
            "دقیقاً چه مسئولیتی را می‌توان با اطمینان به این فرد سپرد؟"
        ),
        requirements=(
            "Flag Profile کامل",
            "Real Project Evidence",
            "Replay",
            "Gate History",
            "Evidence Conflict Review",
            "Outcome History",
        ),
        outcomes=(
            "READY",
            "NOT YET",
            "DIFFERENT SCOPE",
        ),
    ),
)

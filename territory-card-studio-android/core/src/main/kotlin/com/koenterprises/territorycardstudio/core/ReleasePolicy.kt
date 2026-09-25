package com.koenterprises.territorycardstudio.core

enum class ReleaseDisposition { APPROVED_REFERENCE, CANDIDATE_UNAPPROVED }

data class ReleasePolicyResult(val disposition: ReleaseDisposition, val fieldReleaseAllowed: Boolean, val reason: String)

object ReleasePolicy {
    fun evaluate(status: AssignmentStatus): ReleasePolicyResult = if (status.needsNewCard) {
        ReleasePolicyResult(ReleaseDisposition.CANDIDATE_UNAPPROVED, false, "needs_new_card requires explicit human approval of the generated candidate")
    } else {
        ReleasePolicyResult(ReleaseDisposition.APPROVED_REFERENCE, true, "current reference assignment; downstream release gates still apply")
    }
}

"""Pure cleanup authority: an existing correlated S5 authentication proof."""
def owns_session(status,proofs):
    return not status['Access/LoginBusy'] and any(
        proof.get('correlatedByRepository') is True
        and proof.get('level')==status['Access/CurrentLevel']
        and proof.get('user')==status['Access/CurrentUser']
        and proof.get('loginResultSequence')==status['Access/LoginResultSequence']
        for proof in proofs)

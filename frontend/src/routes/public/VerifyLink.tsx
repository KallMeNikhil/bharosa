import { useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { Container, Loading } from "../../components/ui";
import { checkCode } from "../../lib/verification";

export function VerifyLink() {
  const location = useLocation();
  const navigate = useNavigate();
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const link = `${window.location.origin}${location.pathname}${location.search}`;
    void checkCode(link).then((outcome) => {
      navigate("/verify/result", { replace: true, state: outcome });
    });
  }, [location.pathname, location.search, navigate]);

  return (
    <Container>
      <div className="verify-result-page">
        <span className="eyebrow">Verify a product</span>
        <h1 className="page-title">Checking this pack…</h1>
        <Loading label="Checking" />
      </div>
    </Container>
  );
}

export interface Layer {
  index: string;
  name: string;
  question: string;
  proves: string;
  notProves: string;
}

export const LAYERS: Layer[] = [
  {
    index: "01",
    name: "Digital identity",
    question: "Was this payload signed by a legitimate, authorized issuer?",
    proves: "This identity was signed by a key that belonged to this manufacturer, and that key's current trust status.",
    notProves: "That the physical pack in front of the verifier is the one the identity was issued for — a photographed code passes identically to a genuine one.",
  },
  {
    index: "02",
    name: "Physical identity",
    question: "Does the object in hand match a concealed feature only the genuine pack carries?",
    proves: "Someone with physical access to this specific pack triggered this verification, at least once.",
    notProves: "That the contents of the pack are unmodified — dilution or refilling after a legitimate first opening is invisible to this mechanism.",
  },
  {
    index: "03",
    name: "Supply-chain identity",
    question: "Did this identity move through a graph of legitimate custody?",
    proves: "Whether an identity's observed movement is consistent with a legitimate path from manufacturer to retailer.",
    notProves: "Any single event's legitimacy in isolation — a lateral or backward movement can be entirely normal.",
  },
  {
    index: "04",
    name: "Behavioral identity",
    question: "Is the observed pattern consistent with one object existing in one place at a time?",
    proves: "Aggregate consistency, or inconsistency, with how one genuine object moves through the world — expressed as evidence strength.",
    notProves: "Certainty. A single anomalous signal is never sufficient grounds for a fraud conclusion on its own.",
  },
];

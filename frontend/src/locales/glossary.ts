export interface GlossaryTerm {
  term: string;
  hindiTerm: string;
  simpleExplanation: string;
  hindiExplanation: string;
  regulatoryReference?: string;
  showEnglishAlongside: boolean;
}

export const INSURANCE_GLOSSARY: Record<string, GlossaryTerm> = {
  moratorium: {
    term: "Moratorium Period",
    hindiTerm: "मोराटोरियम अवधि (60 महीने की रोक)",
    simpleExplanation:
      "After 60 months of continuous policy coverage, the insurer cannot dispute or reject a claim on grounds of non-disclosure or misrepresentation (except proven fraud).",
    hindiExplanation:
      "लगातार 60 महीनों के प्रीमियम भुगतान के बाद, बीमा कंपनी गैर-प्रकटीकरण (non-disclosure) के आधार पर क्लेम खारिज नहीं कर सकती (सिवाय साबित धोखाधड़ी के)।",
    regulatoryReference: "IRDAI Master Circular 2024, Clause 16(b)",
    showEnglishAlongside: true,
  },
  crc: {
    term: "Claims Review Committee (CRC)",
    hindiTerm: "दावा समीक्षा समिति (CRC)",
    simpleExplanation:
      "Mandatory internal committee of the insurance company. By law, no claim can be rejected without CRC review and formal approval.",
    hindiExplanation:
      "बीमा कंपनी की आंतरिक समिति। IRDAI नियमों के तहत बिना CRC की पूर्व मंजूरी के कोई भी क्लेम रिजेक्ट नहीं किया जा सकता।",
    regulatoryReference: "IRDAI Master Circular 2024, Clause 19(a)",
    showEnglishAlongside: true,
  },
  ped: {
    term: "Pre-Existing Disease (PED)",
    hindiTerm: "पूर्व-विद्यमान बीमारी (PED)",
    simpleExplanation:
      "Medical conditions diagnosed or treated prior to purchasing the policy. Typically subject to a waiting period of up to 36 months.",
    hindiExplanation:
      "पॉलिसी खरीदने से पहले से मौजूद बीमारी। इसके लिए IRDAI ने अधिकतम 36 महीने का वेटिंग पीरियड तय किया है।",
    regulatoryReference: "IRDAI Health Insurance Regulations 2024",
    showEnglishAlongside: true,
  },
  copay: {
    term: "Co-payment",
    hindiTerm: "सह-भुगतान (Co-pay)",
    simpleExplanation:
      "A fixed percentage of the claim amount that the policyholder agreed to bear out-of-pocket per policy terms.",
    hindiExplanation:
      "क्लेम राशि का पूर्व-निर्धारित प्रतिशत जिसे पॉलिसीधारक को स्वयं वहन करना होता है।",
    regulatoryReference: "Policy Terms & Conditions",
    showEnglishAlongside: true,
  },
  roomRentLimit: {
    term: "Room Rent Sub-limit & Proportionate Deduction",
    hindiTerm: "कमरा किराया उप-सीमा व आनुपातिक कटौती",
    simpleExplanation:
      "If you choose a hospital room above your eligible limit, associated medical charges are deducted proportionately.",
    hindiExplanation:
      "यदि आप अनुमत सीमा से अधिक किराए का कमरा चुनते हैं, तो डॉक्टर फीस व नर्सिंग शुल्क में आनुपातिक कटौती की जाती है।",
    regulatoryReference: "IRDAI Master Circular 2024",
    showEnglishAlongside: true,
  },
};

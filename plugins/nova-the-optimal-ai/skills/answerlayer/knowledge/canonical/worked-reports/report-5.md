# **Expert-Level Compliance Architecture: Coping with CA AI Employment Discrimination Law (Post-Oct 2025 Framework)**

The regulatory landscape governing the use of Artificial Intelligence (AI) in employment within California is defined by a complex, dual-jurisdictional architecture. Effective compliance requires covered entities to navigate the anti-discrimination mandates of the Civil Rights Department (CRD) under the Fair Employment and Housing Act (FEHA) concurrently with the transparency and privacy obligations imposed by the California Privacy Protection Agency (CPPA) under the California Consumer Privacy Act (CCPA/CPRA). Successful governance necessitates a synchronized strategy focused on vendor accountability, continuous technical auditing, and strategic workflow design.

## **I. The Dual Regulatory Architecture: CRD (FEHA) vs. CPPA (CCPA)**

California AI employment compliance is fundamentally a dual-jurisdictional challenge, necessitating simultaneous adherence to two distinct regulatory streams with differing effective dates, scope, and compliance mechanisms.

### **1.1 Temporal and Functional Bifurcation: Effective Dates and Triggers**

Compliance obligations began in late 2025, but the full scope of requirements is phased, forcing employers to manage immediate anti-bias demands while phasing in privacy infrastructure.

The **CRD (FEHA) Regulations**, focused purely on preventing algorithmic discrimination, took effect on **October 1, 2025**.1 These regulations apply to employers with five or more employees in California 4 and clarify that existing anti-discrimination protections of FEHA explicitly apply to employment decisions or selection criteria facilitated by Automated Decision Systems (ADS).5

The **CPPA (CCPA/CPRA) Regulations**, which govern transparency, access, and consumer choice (opt-out), are phased in over a longer period.7 Mandatory compliance for initiating high-risk processing, which triggers the requirement for **Risk Assessments**, began on **January 1, 2026**.8 Businesses must complete these assessments before covered processing begins.8 Documentation outlining these risk assessments for activities initiated before the effective date and continuing after must be submitted to the CPPA by **April 1, 2028**.7 Finally, mandatory compliance for core **ADMT (Notice/Opt-Out/Access)** obligations is set for **January 1, 2027**.7 This staggered timeline means compliance requires immediate CRD anti-bias due diligence while simultaneously initiating the long-term process implementation required by the CPPA.10

### **1.2 Definitional Divergence and Scope Mapping (ADS vs. ADMT)**

The differing statutory scopes of the two agencies create a critical requirement for internal policy coherence. The CRD’s definition of technology is significantly broader than the CPPA’s, covering nearly all computational tools used in HR.

The **CRD definition of Automated Decision System (ADS)** is defined as a computational process that **"makes a decision or facilitates human decision making"** regarding an employment benefit.2 The inclusion of *facilitation* ensures wide coverage over tools used for resume screening, performance evaluations, productivity monitoring, directed recruiting (job advertisements), and analyzing third-party data.4 The system applies regardless of whether the technology utilizes advanced machine learning, algorithms, statistics, or other data processing techniques.2

Conversely, the **CPPA definition of Automated Decision-Making Technology (ADMT)** is narrower, defined as technology that **"replaces or substantially replaces human decision-making"** when processing personal information for a "Significant Decision".7 Employment is explicitly designated as a "Significant Decision".10 Crucially, technologies that incorporate **"meaningful human involvement"** (MHI) are potentially exempt from the onerous CPPA ADMT notice and opt-out requirements.10

The strategic consequence of this divergence is that organizations must manage the immediate and critical risk of CRD anti-discrimination liability (beginning October 2025\) while strategically designing the operational workflow to ensure Meaningful Human Involvement. By maintaining documented MHI, an organization can potentially avoid the complex, resource-intensive CPPA requirements for detailed Pre-Use Notice, Opt-Out mechanisms, and Access Rights that take effect in 2027\.7 This initial strategic decision—investing in MHI documentation and CRD anti-bias testing versus building out full CPPA ADMT infrastructure—is the central risk mitigation trade-off in the early compliance phase.

Table 1: Dual Regulatory Compliance Matrix (CRD vs. CPPA)

| Compliance Domain | CRD (FEHA Anti-Discrimination) | CPPA (CCPA Privacy/Access) | Point of Conflict/Nuance |
| :---- | :---- | :---- | :---- |
| **Governing Regulation** | FEHA (Fair Employment and Housing Act) | CCPA/CPRA (California Privacy Rights Act) | Different enforcement agencies and legal mandates. |
| **Technology Definition** | ADS: Makes or *facilitates* human decision-making 11 | ADMT: *Replaces or substantially replaces* human decision-making 7 | ADMT is narrower, requiring replacement. ADS is broader (facilitation).7 |
| **Effective Date** | October 1, 2025 1 | Phased: Risk Assessments Jan 1, 2026; ADMT Compliance Jan 1, 2027 7 | Requires immediate CRD compliance concurrent with CPPA planning/risk assessment initiation. |
| **Primary Obligation** | Prevent Disparate Impact/Treatment; Maintain 4-year records of ADS Data 2 | Provide Pre-Use Notice, Opt-Out Rights, Access Rights; Conduct Risk Assessments 7 | CRD is outcome-focused (bias); CPPA is process-focused (transparency/choice). |
| **Compliance Mechanism** | Anti-Bias Testing (Affirmative Defense) 6 | Risk Assessments and Notice Protocols 7 | Testing is essential for CRD defense; MHI can exempt from core ADMT rules.7 |

### **1.3 Scope of Coverage and High-Risk Edge Cases**

The regulations provide explicit examples of high-risk activities considered to be Automated Decision Systems.3 These activities often utilize sensitive input data or proxy metrics that can inadvertently discriminate. Covered high-risk activities include analyzing facial expressions, word choice, or voice in online interviews.4 The analysis of characteristics like tone of voice or mannerisms may potentially discriminate based on protected characteristics such as race, gender, or disability.6 Further, if an ADS assessment elicits information about a disability, such as a test measuring reaction time or skill, it may constitute an unlawful medical inquiry, triggering the FEHA reasonable accommodation requirements.6 Other covered uses include computer-based assessments (puzzles, games) to measure skills or aptitude, screening resumes for specific terms or patterns, and analyzing employee or applicant data acquired from third parties.3

The regulations also explicitly expand the scope of liability by defining "employer" to include any **agent** acting directly or indirectly on behalf of the employer in making employment decisions, including those assisted by ADS.5 This definition directly implicates third-party AI vendors.15 This regulatory clarity emphasizes that accountability cannot be outsourced merely through the selection of a third-party tool.

Finally, the regulatory framework is stabilized by the October 2025 veto of SB 7, the "No Robo Bosses Act," which would have prohibited employers from relying "solely" on an ADS for discipline or termination decisions.17 The Governor cited the need to assess the impact of the newly finalized CRD/CPPA regulations, confirming that the current dual framework is the authoritative compliance text for the immediate future.17

## **II. CRD Compliance Stream: Anti-Discrimination Mandates and Affirmative Defense**

The CRD framework is primarily concerned with preventing discrimination, whether intentional (disparate treatment) or unintentional (disparate impact), caused by algorithmic bias.2 The core legal protection for employers lies in establishing a verifiable record of due diligence.

### **2.1 Prohibited Practices and Disparate Impact Liability**

It is strictly unlawful for a covered entity to use an ADS or selection criteria that results in discrimination based on any protected characteristic under FEHA.2 The regulations specifically highlight potential scenarios where ADS tools create unlawful proxy discrimination. For instance, systems that analyze an applicant's skill or reaction time may inherently disadvantage individuals with certain disabilities, requiring the employer to provide a reasonable accommodation consistent with FEHA disability protections.6 Similarly, analyzing non-cognitive characteristics such as tone of voice or facial expressions can serve as a proxy for protected characteristics, thereby violating the prohibition against discrimination based on race, national origin, or disability.6

Employers must proactively address the intersection of algorithmic assessment and reasonable accommodation requirements. If an ADS is identified as measuring or assessing a characteristic that puts a protected class at a disadvantage, accommodations must be provided to avoid unlawful discrimination.6

### **2.2 Operationalizing the Affirmative Defense (CRD § 11009(f))**

The regulations introduce an affirmative defense that provides the only clear path for employers to defend against a discrimination claim based on the use of an ADS. To establish this defense, employers must demonstrate they performed **"anti-bias testing or similar proactive efforts to avoid unlawful discrimination"** both **prior to and after** adopting the ADS.6

The efficacy of this defense is judged based on six specific factors 6:

1. **Quality** of the anti-bias testing performed.  
2. **Efficacy** of the testing methods used to detect bias.  
3. **Recency** (frequency) of the testing.  
4. **Scope** of the testing (i.e., which protected groups and outcomes were analyzed).  
5. The verifiable **results** of the testing or other due diligence.  
6. The employer's documented **response** to the results, detailing how and whether the employer mitigated any identified issues.6

The inclusion of "Recency" and a required "Response to the results" fundamentally demands that compliance efforts move beyond static, one-time audits. Given that AI models are prone to decay and data drift over time, the only way to satisfy the "recency" and demonstrate a continuous "response to results" is through implementing a **Continuous Monitoring System** for ADS within the MLOps pipeline. This shifts the operational requirement from sporadic checks to ongoing, automated bias detection and mitigation, essential for maintaining a successful legal defense.

### **2.3 Statistical Auditing: Contested Wisdom and Technical Defensibility**

While the CRD framework focuses heavily on the quality and efficacy of anti-bias testing, it intentionally **does not mandate** specific statistical thresholds for disparate impact, such as the federal EEOC’s 4/5ths Rule.18 The CRD’s "Final Statement of Reasons" does not provide detailed reasoning for rejecting the 4/5ths Rule nor suggest alternative metrics, creating a gap that the technical implementation team must fill with advanced practices.18

Legal consensus suggests that relying solely on the 4/5ths rule, which tolerates selection rates 20% lower for disadvantaged groups, is poor policy and likely insufficient to satisfy the CRD's stringent "Quality and Efficacy" factors.20 To establish technical defensibility, employers must leverage advanced statistical fairness metrics that are common in AI ethics research. Tools like the open-source **AI Fairness 360 (AIF360)** toolkit provide over seventy metrics, including key indicators such as **Statistical Parity Difference**, **Equal Opportunity Difference**, and **Average Odds Difference**.21 Utilization of these metrics is necessary to demonstrate rigorous due diligence that meets the required standard under FEHA.

Furthermore, compliance with the CRD framework includes a stringent **Recordkeeping Mandate**: employers must securely store all data related to the ADS, referred to as "Automated-Decision System Data," for a minimum of **four years**.2 This mandate requires robust data archiving and extraction capabilities, often presenting a technical challenge when integrating with third-party vendor platforms.

## **III. CPPA Compliance Stream: Transparency, Access, and Risk Assessment**

The CPPA mandates focus on the process surrounding the use of ADMT, ensuring consumer control over the high-risk processing of their personal information (PI), which includes PI belonging to applicants and employees.7

### **3.1 Mandatory Risk Assessments and Timeline**

Businesses subject to CCPA requirements must conduct a detailed Risk Assessment for any data processing that presents a "significant risk" to California residents' privacy, including the use of ADMT for employment-related Significant Decisions.8

The assessment must be completed **before** a business initiates covered processing.8 The content must be detailed and prescriptive, analyzing and documenting potential privacy harms.8 The assessment must be updated at least once every three years or immediately upon any material change to the processing that affects risks or safeguards.8 Operationally, the employer must obtain a **written attestation from a company executive** confirming the assessment.10 While the underlying risk assessment document itself is not submitted to the CPPA, information regarding the assessments (contact, time period, number conducted) must be submitted by April 1, 2028, for ongoing activities.7

### **3.2 Pre-Use Notice Requirements (CPPA ADMT)**

If the use of ADMT constitutes a Significant Decision *without* meaningful human involvement, the business must provide a detailed Pre-Use Notice to California residents **at or before** collecting personal information for ADMT use.7 The notice must be presented prominently, conspicuously, and in a manner that is understandable and accessible to consumers with disabilities.23

The notice must provide a highly technical description of the process, including the following mandatory elements 7:

* The **specific purpose** for which the ADMT will be used.10  
* A description of **how the ADMT works** and the logic involved in the decision-making process.7  
* The **categories of personal information** that explicitly affect the ADMT's output.10  
* The **type of output** generated (e.g., prediction, score).10  
* A description of **how that output would be used** in making the decision, detailing whether it was the sole factor, if other factors were involved, and the role of any human review.23  
* The consumer’s right to **opt-out** and a description of the **alternative decision-making process** available if the consumer exercises this right.7

An employer may provide a **consolidated notice** under specific conditions, such as when using a single ADMT for multiple purposes (e.g., productivity monitoring used for work assignment *and* compensation decisions), or when using multiple ADMTs for a single purpose (e.g., separate software tools for resume screening and voice analysis used for hiring).25

### **3.3 The "Meaningful Human Involvement" Escape Clause**

The strategic path to avoiding the CPPA’s stringent notice and opt-out requirements lies in demonstrating that the ADMT does not "substantially replace" human decision-making.7 This requires documented and rigorous human oversight. To qualify as **Meaningful Human Involvement (MHI)**, the human review process must satisfy three criteria 7:

1. The human must **understand how to interpret the technology's output**.7  
2. The human must **consider the output alongside other relevant information**.7  
3. The human must have the **authority to change the decision** based on their review.7

Operationally, merely having a human reviewer present to "rubber-stamp" an algorithmic decision is insufficient.7 Effective MHI requires documented procedures showing that human reviewers analyze the algorithmic output in context, alongside traditional selection factors, and must record their justification if they override the ADMT's recommendation. This level of diligence mitigates CPPA ADMT liability while simultaneously strengthening the CRD’s "response to results" factor for the affirmative defense.

Table 3: CPPA ADMT Pre-Use Notice Requirements (Technical Content)

| Required Notice Component | Technical Specificity Mandate | Example Employment Application |
| :---- | :---- | :---- |
| **Specific Purpose** | Exact reason for using ADMT to make a Significant Decision 7 | *To predict the likelihood of candidate success in Role X based on automated analysis of skills demonstrated in the pre-interview coding assessment.* |
| **How ADMT Works** | Description of the ADMT's process, logic, and computational method (model type) 7 | *Uses a supervised machine learning model (XGBoost) trained on historical performance metrics of current employees.* |
| **Categories of PI Affecting Output** | Detailed categories of personal information inputs that influence the final decision output 10 | *Years of relevant experience (weighted 35%), Normalized time-to-completion score (weighted 40%), and Detected emotional valence during video analysis (weighted 25%).* |
| **Usage of Output** | Explicit statement on whether the output is the sole factor, or one of several factors, and description of the human role 23 | *Output generates an Applicant Risk Ranking (1-5). The ranking constitutes 70% of the initial screening decision. A Human Recruiter reviews the bottom 25% for manual override.* |

## **IV. Vendor and Agent Liability Management: Mitigating Third-Party Risk**

The use of third-party Applicant Tracking Systems (ATS) and AI screening tools represents a critical risk area, as the employer is ultimately responsible for the discriminatory outputs of the system.2 Legal teams must address the expanding definition of vendor liability through aggressive contractual negotiation.

### **4.1 Agency Theory and Expanded Liability**

California law and emerging judicial precedent treat AI vendors as direct "agents" of the employer.5 The FEHA regulations define an agent as one who exercises a function traditionally performed by the employer, such as applicant screening or hiring.5 This classification means that AI vendors performing functions like screening are delegated responsibility for employment decisions.15

Judicial decisions have upheld this theory, holding AI vendors directly liable for discriminatory hiring decisions (e.g., class action lawsuits involving Workday).15 The fundamental issue is that when bias is embedded in the AI system, it scales rapidly, turning what were minor, localized biases into mass discrimination events subject to class action litigation.26

This dynamic creates an immediate contractual conflict, often referred to as the "indemnification squeeze." Standard Software as a Service (SaaS) contracts frequently contain broad indemnification clauses requiring the customer (the employer) to hold the vendor harmless for discriminatory outcomes, even if the underlying bias originates from defects in the vendor's proprietary algorithm or training data.15 This transfers existential legal risk from the vendor, who created the flawed tool, back to the employer.15

### **4.2 Contractual Risk Mitigation: Mandatory Clauses**

Legal teams must approach AI vendor negotiations as primary risk management exercises. Since only a small minority of vendors (estimated at 17%) provide warranties for regulatory compliance, highly specific contractual carve-outs must be demanded.15

Key provisions include:

* **Compliance Warranties:** Requiring explicit warranties that the AI tool, including the underlying model and its outputs, is compliant with all applicable CA employment regulations (FEHA/CCPA).15  
* **Audit Rights and Data Access:** Mandating robust audit rights that allow the customer to examine algorithmic decision-making, bias testing methodologies, and crucially, access to all "Automated-Decision System Data".15 This technical access is non-negotiable, as the employer cannot satisfy the CRD's six-factor affirmative defense requirement without the vendor's underlying data and methodologies.6  
* **Indemnification for Bias:** Negotiating for the vendor to indemnify the customer against discrimination and bias claims specifically caused by the AI tool’s defective design, training data, or flawed outputs.15 This clause must function as a carve-out that overrides general indemnity provisions favoring the vendor.  
* **Model Control and Financial Backstops:** Requiring vendors to maintain specific insurance coverage (cyber liability, technology errors and omissions).27 For tools utilizing third-party Large Language Models (LLMs), contracts should require the employer’s prior written approval for any changes or introduction of new core models, ensuring the employer retains control over foundational risk inputs.27

Table 2: Prescriptive AI Vendor Contract Clauses for CA Compliance

| Risk Area | Required Contractual Carve-Out/Clause | Rationale/Citation |
| :---- | :---- | :---- |
| **Discrimination Liability Shift** | Explicit, uncapped indemnification for the Customer against claims arising from discrimination/bias caused by the AI tool’s flawed outputs or design 15 | CA law treats vendor as an employer's agent; shifts existential legal risk back to the tool creator.5 |
| **Bias Testing Warranty** | Vendor warrants the model was validated on diverse datasets, is subject to regular bias audits, and guarantees indemnity for failures in these areas 27 | Directly addresses the CRD's "quality and efficacy" factors for the affirmative defense.6 |
| **Audit/Data Access Right** | Customer retains technical audit rights, access to underlying algorithmic specifications, and all ADS Data necessary for state-specific audit reporting 15 | Essential for satisfying CRD's 4-year data retention and due diligence requirements.2 |
| **LLM Model Control** | Prior written approval required for changes to, or introduction of, LLMs or other core models utilized by the Platform 27 | Ensures employer controls input risk and maintains a stable foundation for bias audits. |

## **V. Operational Implementation and Tooling Ecosystem**

Translating legal requirements into functional compliance requires technical integration, focusing on data extraction, multi-jurisdictional configuration, and embedding governance into the workflow.

### **5.1 HRIS Integration and Data Extraction Challenges**

Compliance success depends heavily on the ability of existing Human Resources Information Systems (HRIS) and ATS platforms (such as Workday or Dayforce) to provide the granular ADS data required for audits.29 Monolithic systems often create an **HRIS Audit Bottleneck**, making it difficult to extract the specific input, intermediate scoring, and final output data, along with demographic subgroups, necessary for defensible bias audits.29 This difficulty complicates both the CRD's four-year data retention mandate 6 and the ability to demonstrate an adequate "response to results" (remediation).6

To counteract this, organizations utilize specialized third-party tools (e.g., PeopleFlow for Workday) to automate testing of HCM configurations, ensuring that compliance metrics can be reliably extracted and validated *before* the system is launched live.30 Compliance teams must mandate specific **Export Definitions** and audit functionalities within their HRIS/ATS configuration (e.g., Dayforce's configuration options) 32, moving beyond general reporting to dedicated compliance data feeds that satisfy the mandatory retention and auditability requirements.3 Secure HRIS integration ensures accurate employee records and consolidated data synchronization across payroll and IT systems, strengthening compliance reporting for regulatory oversight.33

### **5.2 Compliance Configuration Architecture (Multi-State Requirements)**

Organizations operating nationally must implement a compliance architecture capable of dynamically adapting to a patchwork of state-level AI regulation.34 This presents three key configuration challenges:

1. **The Documentation Configuration Challenge:** The system must generate highly technical specifications required by CA regulations while simultaneously producing simpler, generalized disclosure materials required by other states.34  
2. **The Audit Configuration Challenge:** The organization must manage relationships with AI vendors capable of providing the varying levels of technical access required by different jurisdictions. California's six-factor defense 6 requires detailed algorithmic specification, whereas other states might accept outcome analysis alone.34  
3. **The Transparency Configuration Challenge:** Compliance requires implementing candidate communication systems capable of dynamically generating **state-appropriate disclosure specificity** based on the applicant's location. The CPPA Pre-Use Notice mandates prescriptive technical information.7 The system must be able to deliver this detailed, geo-fenced communication when required, ensuring timeliness and specificity.34

### **5.3 AI Compliance Tooling and Workforce Adaptation**

The technical foundation for CRD compliance often involves advanced, non-commercial tooling. Open-source toolkits like **AI Fairness 360 (AIF360)**, available in Python and R, offer over 70 fairness metrics, including Statistical Parity Difference and Average Odds Difference.21 These resources provide the technical sophistication needed to move beyond rudimentary analyses and satisfy the CRD's requirement for testing "quality and efficacy".6

Commercial HR technology is integrating compliance-focused features. Vendors like Dayforce are launching AI assistant and collaborative AI workspace environments, aiming to automate compliance management and streamline workflows.35 Furthermore, internal workforce dynamics are evolving; "Colleague AI Agents" are being implemented to assist employees in tasks like checking compliance and answering HR-related questions, suggesting that AI's role is shifting from simply making decisions to actively *assisting* in compliance assurance.37

At the enterprise level, AI governance requires integrated data infrastructure. Best practices, driven by discussions in open-source data communities, indicate that governance must be implemented as a feature, not an afterthought.38 Organizations are developing methods to catalog AI applications and embed structured **Compliance Type Specifications** (e.g., framework identification, compliance status, remediation tracking) directly into their metadata platforms. This strategic integration enables automated compliance reporting necessary for both the CRD's continuous monitoring mandate and the CPPA's future assessment submission requirements.8

## **VI. Conclusions and Strategic Recommendations**

The new California regulatory framework necessitates an integrated, risk-based compliance strategy that prioritizes the existential risk of anti-discrimination claims (CRD) over the process-oriented requirements of privacy (CPPA).

The core strategic action is to rigorously implement a workflow built around **Meaningful Human Involvement (MHI)**. By ensuring human reviewers have the documented understanding, contextual information, and authority to override algorithmic outputs, employers strengthen their CRD affirmative defense while potentially exempting themselves from the complex CPPA ADMT Notice and Opt-Out requirements until 2027\.

Technically, compliance hinges on **continuous auditing** and **vendor control**. Continuous bias monitoring, using sophisticated metrics beyond the 4/5ths rule, must be integrated into the MLOps pipeline to satisfy the CRD’s requirement for recent testing and documented response to results.6 Crucially, organizations must immediately audit and reform AI vendor contracts, mandating indemnification for algorithmically caused bias and guaranteeing technical access to all ADS Data necessary to meet the four-year recordkeeping requirement and conduct independent, defensible audits.2

#### **Works cited**

1. Civil Rights Council Secures Approval for Regulations to Protect Against Employment Discrimination Related to Artificial Intelligence | CRD, accessed October 24, 2025, [https://calcivilrights.ca.gov/2025/06/30/civil-rights-council-secures-approval-for-regulations-to-protect-against-employment-discrimination-related-to-artificial-intelligence/](https://calcivilrights.ca.gov/2025/06/30/civil-rights-council-secures-approval-for-regulations-to-protect-against-employment-discrimination-related-to-artificial-intelligence/)  
2. 10 FAQs About California's New Algorithmic Discrimination Rules \- Ogletree, accessed October 24, 2025, [https://ogletree.com/insights-resources/blog-posts/10-faqs-about-californias-new-algorithmic-discrimination-rules/](https://ogletree.com/insights-resources/blog-posts/10-faqs-about-californias-new-algorithmic-discrimination-rules/)  
3. California's New AI Regulations Take Effect Oct. 1: Here's Your Compliance Checklist, accessed October 24, 2025, [https://www.jacksonlewis.com/insights/californias-new-ai-regulations-take-effect-oct-1-heres-your-compliance-checklist](https://www.jacksonlewis.com/insights/californias-new-ai-regulations-take-effect-oct-1-heres-your-compliance-checklist)  
4. Navigating California's New and Emerging AI Employment Regulations \- Inside Jobs, accessed October 24, 2025, [https://www.insidejobsblog.com/2025/10/01/navigating-californias-new-and-emerging-ai-employment-regulations/](https://www.insidejobsblog.com/2025/10/01/navigating-californias-new-and-emerging-ai-employment-regulations/)  
5. California's New AI Employment Rules: What Employers Need to Know \- Orrick, accessed October 24, 2025, [https://www.orrick.com/en/Insights/2025/08/Californias-New-AI-Employment-Rules-What-Employers-Need-to-Know](https://www.orrick.com/en/Insights/2025/08/Californias-New-AI-Employment-Rules-What-Employers-Need-to-Know)  
6. California Adopts New Employment AI Regulations Effective October 1, 2025 \- Mayer Brown, accessed October 24, 2025, [https://www.mayerbrown.com/en/insights/publications/2025/08/california-adopts-new-employment-ai-regulations-effective-october-1-2025](https://www.mayerbrown.com/en/insights/publications/2025/08/california-adopts-new-employment-ai-regulations-effective-october-1-2025)  
7. CPPA finalizes rules on ADMT, risk assessments, and cybersecurity audits requirements under the CCPA | White & Case LLP, accessed October 24, 2025, [https://www.whitecase.com/insight-alert/cppa-finalizes-rules-admt-risk-assessments-and-cybersecurity-audits-requirements](https://www.whitecase.com/insight-alert/cppa-finalizes-rules-admt-risk-assessments-and-cybersecurity-audits-requirements)  
8. California Finalizes Groundbreaking Regulations on AI, Risk Assessments, and Cybersecurity, Part III \- Ogletree Deakins, accessed October 24, 2025, [https://ogletree.com/insights-resources/blog-posts/california-finalizes-groundbreaking-regulations-on-ai-risk-assessments-and-cybersecurity-part-iii-risk-assessments/](https://ogletree.com/insights-resources/blog-posts/california-finalizes-groundbreaking-regulations-on-ai-risk-assessments-and-cybersecurity-part-iii-risk-assessments/)  
9. Navigating California's New and Emerging AI Employment Regulations | Inside Privacy, accessed October 24, 2025, [https://www.insideprivacy.com/artificial-intelligence/navigating-californias-new-and-emerging-ai-employment-regulations/](https://www.insideprivacy.com/artificial-intelligence/navigating-californias-new-and-emerging-ai-employment-regulations/)  
10. California's Long-Awaited Final Regulations on Automated Decisionmaking Create New Compliance Challenges for Employers | Littler, accessed October 24, 2025, [https://www.littler.com/news-analysis/asap/californias-long-awaited-final-regulations-automated-decisionmaking-create-new](https://www.littler.com/news-analysis/asap/californias-long-awaited-final-regulations-automated-decisionmaking-create-new)  
11. State of California to regulate use of AI in employment \- Berkshire Associates, accessed October 24, 2025, [https://www.berkshireassociates.com/blog/state-of-california-to-regulate-use-of-ai-in-employment](https://www.berkshireassociates.com/blog/state-of-california-to-regulate-use-of-ai-in-employment)  
12. California Regulates the Use of AI in Employment Decisions \- Vorys, accessed October 24, 2025, [https://www.vorys.com/publication-california-regulates-the-use-of-ai-in-employment-decisions](https://www.vorys.com/publication-california-regulates-the-use-of-ai-in-employment-decisions)  
13. The CPPA Finalizes Rules on ADMT, Risk Assessments, and Cybersecurity Audits | Thought Leadership | Baker Botts, accessed October 24, 2025, [https://www.bakerbotts.com/thought-leadership/publications/2025/august/a-101-of-the-cppas-finalizes-rules-on-admt-risk-assessments-and-cybersecurity-audits](https://www.bakerbotts.com/thought-leadership/publications/2025/august/a-101-of-the-cppas-finalizes-rules-on-admt-risk-assessments-and-cybersecurity-audits)  
14. California Finalizes CCPA Regulations for Automated Decision-Making Technology, Risk Assessments and Cybersecurity Audits | Insights | Skadden, Arps, Slate, Meagher & Flom LLP, accessed October 24, 2025, [https://www.skadden.com/insights/publications/2025/10/california-finalizes-cppa-regulations](https://www.skadden.com/insights/publications/2025/10/california-finalizes-cppa-regulations)  
15. AI Vendor Liability Squeeze: Courts Expand Accountability While Contracts Shift Risk, accessed October 24, 2025, [https://www.joneswalker.com/en/insights/blogs/ai-law-blog/ai-vendor-liability-squeeze-courts-expand-accountability-while-contracts-shift-r.html](https://www.joneswalker.com/en/insights/blogs/ai-law-blog/ai-vendor-liability-squeeze-courts-expand-accountability-while-contracts-shift-r.html)  
16. Expanded Liability in California for Artificial Intelligence Tools, Michael Ward \- Our Take, accessed October 24, 2025, [https://ourtake.bakerbotts.com/post/102in70/expanded-liability-in-california-for-artificial-intelligence-tools](https://ourtake.bakerbotts.com/post/102in70/expanded-liability-in-california-for-artificial-intelligence-tools)  
17. California 2025 Legislative Rundown: Key Changes Coming for Employers \- Ogletree, accessed October 24, 2025, [https://ogletree.com/insights-resources/blog-posts/california-2025-legislative-rundown-key-changes-coming-for-employers/](https://ogletree.com/insights-resources/blog-posts/california-2025-legislative-rundown-key-changes-coming-for-employers/)  
18. 1 CIVIL RIGHTS COUNCIL PROPOSED MODIFICATIONS TO ..., accessed October 24, 2025, [http://calcivilrights.ca.gov/wp-content/uploads/sites/32/2025/06/Final-Statement-of-Reasons-regulations-automated-employment-decision-systems.pdf](http://calcivilrights.ca.gov/wp-content/uploads/sites/32/2025/06/Final-Statement-of-Reasons-regulations-automated-employment-decision-systems.pdf)  
19. EEOC Issues Nonbinding Guidance on Permissible Employer Use of Artificial Intelligence to Avoid Adverse Impact Liability Under Title VII \- K\&L Gates, accessed October 24, 2025, [https://www.klgates.com/EEOC-Issues-Nonbinding-Guidance-on-Permissible-Employer-Use-of-Artificial-Intelligence-to-Avoid-Adverse-Impact-Liability-Under-Title-VII-5-31-2023](https://www.klgates.com/EEOC-Issues-Nonbinding-Guidance-on-Permissible-Employer-Use-of-Artificial-Intelligence-to-Avoid-Adverse-Impact-Liability-Under-Title-VII-5-31-2023)  
20. AI Bias Panel Shows EEOC Should Ditch Four-Fifths Rule \- Cohen Milstein, accessed October 24, 2025, [https://www.cohenmilstein.com/ai-bias-panel-shows-eeoc-should-ditch-four-fifths-rule-law360-expert-analysis/](https://www.cohenmilstein.com/ai-bias-panel-shows-eeoc-should-ditch-four-fifths-rule-law360-expert-analysis/)  
21. AI Fairness 360, accessed October 24, 2025, [https://ai-fairness-360.org/](https://ai-fairness-360.org/)  
22. Trusted-AI/AIF360: A comprehensive set of fairness metrics for datasets and machine learning models, explanations for these metrics, and algorithms to mitigate bias in datasets and models. \- GitHub, accessed October 24, 2025, [https://github.com/Trusted-AI/AIF360](https://github.com/Trusted-AI/AIF360)  
23. What to Know about the New CCPA Regulations on Automated Decision-Making Technology \- Securiti, accessed October 24, 2025, [https://securiti.ai/ccpa-automated-decision-making-technology/](https://securiti.ai/ccpa-automated-decision-making-technology/)  
24. CCPA Updates, Cyber, Risk, ADMT, and Insurance Regulations Written Comments Part 4 \- California Privacy Protection Agency, accessed October 24, 2025, [https://cppa.ca.gov/regulations/pdf/part4\_all\_comments\_combined\_redacted\_oral\_not\_included.pdf](https://cppa.ca.gov/regulations/pdf/part4_all_comments_combined_redacted_oral_not_included.pdf)  
25. Modified Text of Proposed Regulations \- California Privacy Protection Agency, accessed October 24, 2025, [https://cppa.ca.gov/regulations/pdf/ccpa\_updates\_cyber\_risk\_admt\_mod\_txt\_pro\_reg.pdf](https://cppa.ca.gov/regulations/pdf/ccpa_updates_cyber_risk_admt_mod_txt_pro_reg.pdf)  
26. AI hiring looked like a win… until the lawsuits started rolling in : r/RecruitmentAgencies, accessed October 24, 2025, [https://www.reddit.com/r/RecruitmentAgencies/comments/1n5n6u2/ai\_hiring\_looked\_like\_a\_win\_until\_the\_lawsuits/](https://www.reddit.com/r/RecruitmentAgencies/comments/1n5n6u2/ai_hiring_looked_like_a_win_until_the_lawsuits/)  
27. AI Service Agreements in Health Care: Indemnification Clauses, Emerging Trends, and Future Risks | ArentFox Schiff, accessed October 24, 2025, [https://www.afslaw.com/perspectives/health-care-counsel-blog/ai-service-agreements-health-care-indemnification-clauses](https://www.afslaw.com/perspectives/health-care-counsel-blog/ai-service-agreements-health-care-indemnification-clauses)  
28. AI in HR: The State- and Local-Led Future of Employer Compliance, accessed October 24, 2025, [https://www.hunton.com/insights/publications/ai-in-hr-the-state-and-local-led-future-of-employer-compliance](https://www.hunton.com/insights/publications/ai-in-hr-the-state-and-local-led-future-of-employer-compliance)  
29. Workday is a steaming pile of shit and I won't even bother filling out applications for organizations that use it anymore. : r/recruitinghell \- Reddit, accessed October 24, 2025, [https://www.reddit.com/r/recruitinghell/comments/1miwaay/workday\_is\_a\_steaming\_pile\_of\_shit\_and\_i\_wont/](https://www.reddit.com/r/recruitinghell/comments/1miwaay/workday_is_a_steaming_pile_of_shit_and_i_wont/)  
30. PeopleFlow – AI-Powered Workday Test Automation | Smarter Workday Testing, accessed October 24, 2025, [https://www.peopleflow.io/](https://www.peopleflow.io/)  
31. PeopleFlow – AI-Powered Workday Test Automation, accessed October 24, 2025, [https://www.peopleflow.io/workday-support](https://www.peopleflow.io/workday-support)  
32. How the Integration Works \- Dayforce Help Portal, accessed October 24, 2025, [https://help.dayforce.com/r/ImplementationGuide/Dayforce-Implementation-Guide/How-the-Integration-Works](https://help.dayforce.com/r/ImplementationGuide/Dayforce-Implementation-Guide/How-the-Integration-Works)  
33. What Is HRIS Integration? What It Is \+ Process \+ Benefits \- CloudEagle.ai, accessed October 24, 2025, [https://www.cloudeagle.ai/resources/glossaries/what-is-hris-integration](https://www.cloudeagle.ai/resources/glossaries/what-is-hris-integration)  
34. Multi-State AI Compliance: Your Action Plan for Navigating the Regulatory Patchwork \- AMS, accessed October 24, 2025, [https://www.amsinform.com/pre-employment-checks/multi-state-ai-compliance-your-action-plan-for-navigating-the-regulatory-patchwork/](https://www.amsinform.com/pre-employment-checks/multi-state-ai-compliance-your-action-plan-for-navigating-the-regulatory-patchwork/)  
35. Why Compliance is HR Tech's \#1 Topic in 2025 \+ How AI Frees HR for Strategic Work, accessed October 24, 2025, [https://www.youtube.com/watch?v=nRgWeCSv2bA](https://www.youtube.com/watch?v=nRgWeCSv2bA)  
36. AI-Enhanced People Operations \- Dayforce, accessed October 24, 2025, [https://www.dayforce.com/how-we-help/dayforce/leverage-ai-for-efficiency](https://www.dayforce.com/how-we-help/dayforce/leverage-ai-for-efficiency)  
37. AI-powered success—with more than 1,000 stories of customer transformation and innovation | The Microsoft Cloud Blog, accessed October 24, 2025, [https://www.microsoft.com/en-us/microsoft-cloud/blog/2025/07/24/ai-powered-success-with-1000-stories-of-customer-transformation-and-innovation/](https://www.microsoft.com/en-us/microsoft-cloud/blog/2025/07/24/ai-powered-success-with-1000-stories-of-customer-transformation-and-innovation/)  
38. AI Governance and Compliance Framework for AI Applications · Issue \#23853 · open-metadata/OpenMetadata \- GitHub, accessed October 24, 2025, [https://github.com/open-metadata/OpenMetadata/issues/23853](https://github.com/open-metadata/OpenMetadata/issues/23853)
<a id="readme-top"></a>

# SEED - Data Verification Framework

*A data verification framework specifically developed for automating ETL testing*

---

<!-- TABLE OF CONTENTS --> 

<div>
  <summary>📑 Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built Using</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
  </ol>
</div>


---

<!-- ABOUT THE PROJECT -->
## 💡 About the Project

This is a framework that can perform data verification for various ETL tables available in SEED data teams.
 
- The main aim is to conduct data validations and data quality checks for a given ETL table
- This framework follows '**Configuration-Driven-Development**'  - ⚙️ [CDD](https://stuartwheaton.com/blog/2021-10-13-config-driven-development/)

<p align="right">(<a href="#readme-top">🔝</a>)</p>

---

### 🛠️ Built Using

- Python 3 - https://www.python.org/ (currently using 3.12.4)
- PyTest - https://docs.pytest.org/ (latest Pytest Version)

<p align="right">(<a href="#readme-top">🔝</a>)</p>

---

<!-- GETTING STARTED  --> 
## Getting Started



### 💾 Installation

Please follow detailed instructions to get started with installations:
[Confluence Documentation - Installation Guide](https://syscobt.atlassian.net/wiki/spaces/BSM/pages/4870637624/Test+Automation+installation+guide)

<p align="right">(<a href="#readme-top">🔝</a>)</p>

---

## 🤹 Usage

To start using the framework you can follow the detailed instructions provided:  [Confluence Documentation - Usage](https://syscobt.atlassian.net/wiki/spaces/BSM/pages/4891869437/Test+Automation+-+Run+Book).

<p align="right">(<a href="#readme-top">🔝</a>)</p>

---

<!-- ROADMAP -->
## 🛣️ Roadmap

- [x] POC
  - [x] Framework Structure and Design (CDD)
  - [x] External table support
  - [x] HashiCorp Vault support
  - [x] Logs generation
  - [x] SMTP mail support
- [x] MVP
  - [x] Configuration
    - [x] Default YAML structure
    - [x] Secrets Manager
    - [x] Parameter Store
  - [X] CICD
    - [x] Jenkins Automation Script (groovy)
    - [x] Completeness
    - [x] Duplication
    - [x] Timeliness
    - [x] Accuracy
    - [x] Support Truncate and Load tables without transformation
    - [x] Synthetic Data Generation (Exluding OPCO tables)
    - [x] SCD delete validation
    - [x] SCD update validation
    - [x] SCD insert validation
  - [ ] ETL
    -  [x] Support all capabilities from CICD mode
    -  [x] Configure to run via DAGs towards ending task

- [x] V1
  - [X] CICD
    - [x] Rule based validation (phase-1)
    - [ ] Rule based validation (phase-2) (WIP) `🚧`
    - [x] Consistency (phase-1)
    - [x] Consistency (phase-2)
    - [ ] Consistency (phase-3 WIP) `🚧`
    - [ ] Update Synthetic data feature for OPCO table (WIP) `🚧`
    - [ ] Source decrypt multi-file reading support
    - [ ] Enhance SCD validation for business keys (Conform Tables)
    - [ ] Support complex transformation
    - [ ] RI process validation capability
  - [ ] ETL
    -  [x] Support all capabilities from CICD mode
    -  [ ] Capability to run at any phase in Airflow


<p align="right">(<a href="#readme-top">🔝</a>)</p>

---

<!-- CONTRIBUTING -->
## 🤝 Contributing

Contributions are what makes us to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

---
<!-- Git Strategy -->
## 🛠️ Git Strategy


<!-- TABLE OF CONTENTS -->
<div>
  <summary>📑 Naming Conventions for Branches</summary>
  <ul>
    <li>Feature: feature/JIRA_ID/feature_name</li>
    <li>Hot Fix: hotfix/INCIDENT_ID</li>
    <li>Develop: dev</li>
    <li>Main: master</li>
    <li>Release: release/release-1.0.0</li>
    <li>
      Example Steps
      <ul>
        <li>git checkout dev</li>
        <li>git checkout -b release/1.0.0</li>
        <li>git push origin release/1.0.0</li>
        <li>git checkout master</li>
        <li>git merge --no-ff release/1.0.0</li>
        <li>git tag -a v1.0.0 -m "Release 1.0.0"</li>
        <li>git push --tags</li>
        <li>git push origin master</li>
      </ul>
    </li>
  </ul>
</div>

Confluence documentation for full details of git..

🔗 Git [Confluence  - git strategy documentation](https://syscobt.atlassian.net/wiki/spaces/BSM/pages/5107721986/Git+Repo+Setup+Structure+and+Branching+Strategy)



You can also explore the Confluence documentation for comprehensive and regularly updated information.
📚 [Confluence  - Automation Related Documents](https://syscobt.atlassian.net/wiki/spaces/BSM/pages/4425063424/QE+Automation+Data+engineering+focused)

---


🙏 Thanks again!

<p align="right">(<a href="#readme-top">🔝</a>)</p>

# Stage 1 Candidate Retrieval Report (Bangalore 10-User Ecosystem)

## Baseline Configuration
- **Location**: Bangalore, India (50km radius)
- **Hard Constraints**: Mutual age bounds, mutual gender preferences, and location distance satisfied 100%.
- **Retrieval Method**: pgvector Cosine Distance on 1536-dim text-embedding-3-small embeddings.
- **Scoring Formula**: `Combined Score = 0.5 * (Self->Wants Sim) + 0.5 * (Wants<-Self Sim)`.

## Summary Retrieval Matrix

| Primary User | Gender/Age | Candidates Retrieved | #1 Top Candidate | #1 Combined Score | #1 Forward Sim | #2 Candidate | #2 Combined Score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `68374cf7` | male, 33 | 5 | `4ba84372` | **0.0697** | 0.0000 | `5d58ecbb` | 0.0573 |
| `287a2dbd` | male, 30 | 5 | `5d58ecbb` | **0.1746** | 0.0699 | `4ba84372` | 0.1003 |
| `ce4555f5` | female, 31 | 6 | `bd81d058` | **0.1479** | 0.0120 | `ae548ec5` | 0.0245 |
| `c10e8d5c` | male, 29 | 5 | `3a68a2c5` | **0.2302** | 0.2208 | `4ba84372` | 0.1297 |
| `4ba84372` | female, 28 | 6 | `ae548ec5` | **0.1911** | 0.1894 | `c10e8d5c` | 0.1297 |
| `91d1ee6c` | female, 28 | 6 | `c10e8d5c` | **0.0957** | 0.1914 | `99c9c7d6` | 0.0601 |
| `5d58ecbb` | female, 29 | 6 | `287a2dbd` | **0.1746** | 0.2793 | `bd81d058` | 0.1727 |
| `ae548ec5` | male, 30 | 5 | `3a68a2c5` | **0.2020** | 0.0000 | `4ba84372` | 0.1911 |
| `bd81d058` | male, 28 | 5 | `5d58ecbb` | **0.1727** | 0.0000 | `ce4555f5` | 0.1479 |
| `99c9c7d6` | male, 29 | 5 | `3a68a2c5` | **0.1732** | 0.1845 | `91d1ee6c` | 0.0601 |
| `3a68a2c5` | female, 28 | 6 | `c10e8d5c` | **0.2302** | 0.2397 | `ae548ec5` | 0.2020 |

---
## Detailed Candidate Rankings (Full Ordered Shortlists for Every User)

### Primary User: `68374cf7` (male, age 33)
- **User ID**: `68374cf7-8c4d-433f-9786-24834b40083e`
- **Total Retrieved Candidates**: 5

| Rank | Candidate | Gender/Age | Distance | Combined Score | Forward Sim (A.wants->B.self) | Reverse Sim (B.wants->A.self) |
| --- | --- | --- | --- | --- | --- | --- |
| **#1** | `4ba84372` | female, 28 | 15.5 km | **0.0697** | 0.0000 | 0.1394 |
| **#2** | `5d58ecbb` | female, 29 | 19.1 km | **0.0573** | 0.0425 | 0.0720 |
| **#3** | `ce4555f5` | female, 31 | 13.1 km | **0.0148** | 0.0000 | 0.0296 |
| **#4** | `3a68a2c5` | female, 28 | 16.8 km | **0.0000** | 0.0000 | 0.0000 |
| **#5** | `91d1ee6c` | female, 28 | 16.8 km | **0.0000** | 0.0000 | 0.0000 |

### Primary User: `287a2dbd` (male, age 30)
- **User ID**: `287a2dbd-bdc4-4f40-a260-2ba697e6a9fa`
- **Total Retrieved Candidates**: 5

| Rank | Candidate | Gender/Age | Distance | Combined Score | Forward Sim (A.wants->B.self) | Reverse Sim (B.wants->A.self) |
| --- | --- | --- | --- | --- | --- | --- |
| **#1** | `5d58ecbb` | female, 29 | 5.3 km | **0.1746** | 0.0699 | 0.2793 |
| **#2** | `4ba84372` | female, 28 | 4.8 km | **0.1003** | 0.2005 | 0.0000 |
| **#3** | `3a68a2c5` | female, 28 | 5.2 km | **0.0904** | 0.1807 | 0.0000 |
| **#4** | `91d1ee6c` | female, 28 | 5.2 km | **0.0000** | 0.0000 | 0.0000 |
| **#5** | `ce4555f5` | female, 31 | 3.4 km | **0.0000** | 0.0000 | 0.0000 |

### Primary User: `ce4555f5` (female, age 31)
- **User ID**: `ce4555f5-d0b8-4ac1-b06e-6310deb4aa86`
- **Total Retrieved Candidates**: 6

| Rank | Candidate | Gender/Age | Distance | Combined Score | Forward Sim (A.wants->B.self) | Reverse Sim (B.wants->A.self) |
| --- | --- | --- | --- | --- | --- | --- |
| **#1** | `bd81d058` | male, 28 | 7.9 km | **0.1479** | 0.0120 | 0.2838 |
| **#2** | `ae548ec5` | male, 30 | 7.4 km | **0.0245** | 0.0000 | 0.0490 |
| **#3** | `68374cf7` | male, 33 | 13.1 km | **0.0148** | 0.0296 | 0.0000 |
| **#4** | `c10e8d5c` | male, 29 | 7.4 km | **0.0147** | 0.0295 | 0.0000 |
| **#5** | `99c9c7d6` | male, 29 | 8.1 km | **0.0000** | 0.0000 | 0.0000 |
| **#6** | `287a2dbd` | male, 30 | 3.4 km | **0.0000** | 0.0000 | 0.0000 |

### Primary User: `c10e8d5c` (male, age 29)
- **User ID**: `c10e8d5c-9913-4039-85b1-0f928c110b0a`
- **Total Retrieved Candidates**: 5

| Rank | Candidate | Gender/Age | Distance | Combined Score | Forward Sim (A.wants->B.self) | Reverse Sim (B.wants->A.self) |
| --- | --- | --- | --- | --- | --- | --- |
| **#1** | `3a68a2c5` | female, 28 | 5.1 km | **0.2302** | 0.2208 | 0.2397 |
| **#2** | `4ba84372` | female, 28 | 3.7 km | **0.1297** | 0.0000 | 0.2594 |
| **#3** | `91d1ee6c` | female, 28 | 5.1 km | **0.0957** | 0.0000 | 0.1914 |
| **#4** | `ce4555f5` | female, 31 | 7.4 km | **0.0147** | 0.0000 | 0.0295 |
| **#5** | `5d58ecbb` | female, 29 | 10.0 km | **0.0000** | 0.0000 | 0.0000 |

### Primary User: `4ba84372` (female, age 28)
- **User ID**: `4ba84372-ee83-4cb4-8914-d21e34faec77`
- **Total Retrieved Candidates**: 6

| Rank | Candidate | Gender/Age | Distance | Combined Score | Forward Sim (A.wants->B.self) | Reverse Sim (B.wants->A.self) |
| --- | --- | --- | --- | --- | --- | --- |
| **#1** | `ae548ec5` | male, 30 | 3.7 km | **0.1911** | 0.1894 | 0.1928 |
| **#2** | `c10e8d5c` | male, 29 | 3.7 km | **0.1297** | 0.2594 | 0.0000 |
| **#3** | `287a2dbd` | male, 30 | 4.8 km | **0.1003** | 0.0000 | 0.2005 |
| **#4** | `68374cf7` | male, 33 | 15.5 km | **0.0697** | 0.1394 | 0.0000 |
| **#5** | `99c9c7d6` | male, 29 | 0.0 km | **0.0342** | 0.0684 | 0.0000 |
| **#6** | `bd81d058` | male, 28 | 10.4 km | **0.0000** | 0.0000 | 0.0000 |

### Primary User: `91d1ee6c` (female, age 28)
- **User ID**: `91d1ee6c-04f1-49d5-a513-3adffb0da833`
- **Total Retrieved Candidates**: 6

| Rank | Candidate | Gender/Age | Distance | Combined Score | Forward Sim (A.wants->B.self) | Reverse Sim (B.wants->A.self) |
| --- | --- | --- | --- | --- | --- | --- |
| **#1** | `c10e8d5c` | male, 29 | 5.1 km | **0.0957** | 0.1914 | 0.0000 |
| **#2** | `99c9c7d6` | male, 29 | 1.4 km | **0.0601** | 0.0000 | 0.1202 |
| **#3** | `ae548ec5` | male, 30 | 5.1 km | **0.0307** | 0.0614 | 0.0000 |
| **#4** | `bd81d058` | male, 28 | 11.7 km | **0.0254** | 0.0000 | 0.0507 |
| **#5** | `68374cf7` | male, 33 | 16.8 km | **0.0000** | 0.0000 | 0.0000 |
| **#6** | `287a2dbd` | male, 30 | 5.2 km | **0.0000** | 0.0000 | 0.0000 |

### Primary User: `5d58ecbb` (female, age 29)
- **User ID**: `5d58ecbb-5bbe-469c-a993-52c2d3f275e2`
- **Total Retrieved Candidates**: 6

| Rank | Candidate | Gender/Age | Distance | Combined Score | Forward Sim (A.wants->B.self) | Reverse Sim (B.wants->A.self) |
| --- | --- | --- | --- | --- | --- | --- |
| **#1** | `287a2dbd` | male, 30 | 5.3 km | **0.1746** | 0.2793 | 0.0699 |
| **#2** | `bd81d058` | male, 28 | 13.7 km | **0.1727** | 0.3454 | 0.0000 |
| **#3** | `ae548ec5` | male, 30 | 10.0 km | **0.0629** | 0.0333 | 0.0925 |
| **#4** | `68374cf7` | male, 33 | 19.1 km | **0.0573** | 0.0720 | 0.0425 |
| **#5** | `99c9c7d6` | male, 29 | 8.0 km | **0.0358** | 0.0000 | 0.0716 |
| **#6** | `c10e8d5c` | male, 29 | 10.0 km | **0.0000** | 0.0000 | 0.0000 |

### Primary User: `ae548ec5` (male, age 30)
- **User ID**: `ae548ec5-17fc-413c-9489-d3e0336fbff6`
- **Total Retrieved Candidates**: 5

| Rank | Candidate | Gender/Age | Distance | Combined Score | Forward Sim (A.wants->B.self) | Reverse Sim (B.wants->A.self) |
| --- | --- | --- | --- | --- | --- | --- |
| **#1** | `3a68a2c5` | female, 28 | 5.1 km | **0.2020** | 0.0000 | 0.4041 |
| **#2** | `4ba84372` | female, 28 | 3.7 km | **0.1911** | 0.1928 | 0.1894 |
| **#3** | `5d58ecbb` | female, 29 | 10.0 km | **0.0629** | 0.0925 | 0.0333 |
| **#4** | `91d1ee6c` | female, 28 | 5.1 km | **0.0307** | 0.0000 | 0.0614 |
| **#5** | `ce4555f5` | female, 31 | 7.4 km | **0.0245** | 0.0490 | 0.0000 |

### Primary User: `bd81d058` (male, age 28)
- **User ID**: `bd81d058-7166-4b39-b511-6420c933c5ce`
- **Total Retrieved Candidates**: 5

| Rank | Candidate | Gender/Age | Distance | Combined Score | Forward Sim (A.wants->B.self) | Reverse Sim (B.wants->A.self) |
| --- | --- | --- | --- | --- | --- | --- |
| **#1** | `5d58ecbb` | female, 29 | 13.7 km | **0.1727** | 0.0000 | 0.3454 |
| **#2** | `ce4555f5` | female, 31 | 7.9 km | **0.1479** | 0.2838 | 0.0120 |
| **#3** | `91d1ee6c` | female, 28 | 11.7 km | **0.0254** | 0.0507 | 0.0000 |
| **#4** | `4ba84372` | female, 28 | 10.4 km | **0.0000** | 0.0000 | 0.0000 |
| **#5** | `3a68a2c5` | female, 28 | 11.7 km | **0.0000** | 0.0000 | 0.0000 |

### Primary User: `99c9c7d6` (male, age 29)
- **User ID**: `99c9c7d6-47d7-4113-9858-9624b9f68926`
- **Total Retrieved Candidates**: 5

| Rank | Candidate | Gender/Age | Distance | Combined Score | Forward Sim (A.wants->B.self) | Reverse Sim (B.wants->A.self) |
| --- | --- | --- | --- | --- | --- | --- |
| **#1** | `3a68a2c5` | female, 28 | 1.4 km | **0.1732** | 0.1845 | 0.1619 |
| **#2** | `91d1ee6c` | female, 28 | 1.4 km | **0.0601** | 0.1202 | 0.0000 |
| **#3** | `5d58ecbb` | female, 29 | 8.0 km | **0.0358** | 0.0716 | 0.0000 |
| **#4** | `4ba84372` | female, 28 | 0.0 km | **0.0342** | 0.0000 | 0.0684 |
| **#5** | `ce4555f5` | female, 31 | 8.1 km | **0.0000** | 0.0000 | 0.0000 |

### Primary User: `3a68a2c5` (female, age 28)
- **User ID**: `3a68a2c5-f3bd-40d7-8854-4b7d06413589`
- **Total Retrieved Candidates**: 6

| Rank | Candidate | Gender/Age | Distance | Combined Score | Forward Sim (A.wants->B.self) | Reverse Sim (B.wants->A.self) |
| --- | --- | --- | --- | --- | --- | --- |
| **#1** | `c10e8d5c` | male, 29 | 5.1 km | **0.2302** | 0.2397 | 0.2208 |
| **#2** | `ae548ec5` | male, 30 | 5.1 km | **0.2020** | 0.4041 | 0.0000 |
| **#3** | `99c9c7d6` | male, 29 | 1.4 km | **0.1732** | 0.1619 | 0.1845 |
| **#4** | `287a2dbd` | male, 30 | 5.2 km | **0.0904** | 0.0000 | 0.1807 |
| **#5** | `68374cf7` | male, 33 | 16.8 km | **0.0000** | 0.0000 | 0.0000 |
| **#6** | `bd81d058` | male, 28 | 11.7 km | **0.0000** | 0.0000 | 0.0000 |

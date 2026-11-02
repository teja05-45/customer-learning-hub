import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowLeft, Check, Plus, Trash2 } from 'lucide-react'
import { api, fieldErrors } from '../services/api'
import { useToast } from '../app/ToastProvider'
import { useSession } from '../app/SessionProvider'
import type { BusinessFunction, Priority, ProjectDetail, ProjectStatus, ProjectTemplate, Segment } from '../types'
import { ErrorState, Notice, PageHeader, SectionCard } from '../components/ui'
import { BUSINESS_FUNCTION_LABELS, SEGMENT_LABELS, titleCase } from '../utils/format'

const schema = z
  .object({
    name: z.string().min(3, 'Give the project a name of at least 3 characters.').max(200),
    objective: z
      .string()
      .min(10, 'Write the objective as a sentence someone could disagree with.')
      .max(4000),
    description: z.string().max(8000).optional(),
    methodology: z.string().max(80).optional(),
    priority: z.enum(['low', 'medium', 'high', 'critical']),
    status: z.enum(['draft', 'planning', 'recruiting', 'in_progress', 'analysis', 'completed', 'archived']),
    owner_id: z.string().optional(),
    business_functions: z.array(z.string()).min(1, 'Choose at least one business function.'),
    target_segments: z.array(z.string()).min(1, 'Choose at least one customer segment.'),
    start_date: z.string().optional(),
    deadline: z.string().optional(),
  })
  .refine(
    (values) => !values.start_date || !values.deadline || values.deadline >= values.start_date,
    { message: 'Deadline cannot be before the start date.', path: ['deadline'] },
  )

type FormValues = z.infer<typeof schema>

const FORM_FIELDS = new Set([
  'name',
  'objective',
  'description',
  'methodology',
  'priority',
  'status',
  'owner_id',
  'business_functions',
  'target_segments',
  'start_date',
  'deadline',
])

const BUSINESS_FUNCTIONS: BusinessFunction[] = [
  'brand_marketing',
  'product_category',
  'growth',
  'customer_experience',
  'operations',
  'executive',
]

const SEGMENTS: Segment[] = ['first_time_buyer', 'repeat_buyer', 'lapsed_buyer', 'household_buyer']

export function ProjectNewPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const { users } = useSession()
  const [questions, setQuestions] = useState<string[]>([''])
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [serverError, setServerError] = useState<string | null>(null)

  const templates = useQuery({
    queryKey: ['project-templates'],
    queryFn: () => api.get<ProjectTemplate[]>('/projects/templates'),
    staleTime: Infinity,
  })

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: '',
      objective: '',
      description: '',
      methodology: 'Moderated 30-minute interviews (simulated)',
      priority: 'medium',
      status: 'planning',
      business_functions: [],
      target_segments: [],
      owner_id: '',
      start_date: '',
      deadline: '',
    },
  })

  const businessFunctions = watch('business_functions')
  const targetSegments = watch('target_segments')

  const toggle = (field: 'business_functions' | 'target_segments', value: string) => {
    const current = field === 'business_functions' ? businessFunctions : targetSegments
    const next = current.includes(value) ? current.filter((entry) => entry !== value) : [...current, value]
    setValue(field, next, { shouldValidate: true })
  }

  const applyTemplate = (template: ProjectTemplate) => {
    setSelectedTemplate(template.key)
    setValue('name', template.name, { shouldValidate: true })
    setValue('objective', template.objective, { shouldValidate: true })
    setValue('methodology', template.methodology)
    setValue('priority', template.priority)
    setValue('business_functions', template.business_functions, { shouldValidate: true })
    setValue('target_segments', template.target_segments, { shouldValidate: true })
    setQuestions(template.questions)
  }

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      api.post<ProjectDetail>('/projects', {
        ...values,
        owner_id: values.owner_id || null,
        start_date: values.start_date || null,
        deadline: values.deadline || null,
        questions: questions
          .map((text) => text.trim())
          .filter((text) => text.length > 0)
          .map((text) => ({ text })),
      }),
    onSuccess: (project) => {
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.push({
        title: 'Research project created',
        message: `${project.name} is ready for recruitment.`,
        variant: 'success',
      })
      navigate(`/projects/${project.id}`)
    },
    onError: (error) => {
      const fields = fieldErrors(error)
      let matched = false
      Object.entries(fields).forEach(([field, message]) => {
        if (FORM_FIELDS.has(field)) {
          setError(field as keyof FormValues, { message })
          matched = true
        }
      })
      if (!matched) setServerError((error as Error).message)
    },
  })

  return (
    <div className="page" style={{ maxWidth: 1180 }}>
      <Link to="/projects" className="link-quiet inline mb-3">
        <ArrowLeft size={13} /> Back to research projects
      </Link>
      <PageHeader
        title="New research project"
        description="Start with the question and the decision it should inform. Templates fill the shape, never the conclusion."
      />

      <form
        onSubmit={handleSubmit((values) => {
          setServerError(null)
          mutation.mutate(values)
        })}
        noValidate
      >
        <div className="section-grid grid-sidebar">
          <div className="stack stack-3">
            <SectionCard title="Start from a template" subtitle="Optional, but keeps projects comparable">
              {templates.isLoading && <div className="skeleton" style={{ height: 90 }} />}
              {templates.error && (
                <ErrorState message="Templates could not be loaded." onRetry={() => templates.refetch()} />
              )}
              <div className="section-grid grid-2" style={{ gap: 10 }}>
                {templates.data?.map((template) => (
                  <button
                    key={template.key}
                    type="button"
                    onClick={() => applyTemplate(template)}
                    className="role-card"
                    style={{
                      borderColor: selectedTemplate === template.key ? 'var(--clh-primary)' : undefined,
                      background: selectedTemplate === template.key ? 'var(--clh-primary-soft)' : undefined,
                    }}
                  >
                    <span style={{ flex: 1 }}>
                      <span className="role-name d-flex align-items-center gap-2">
                        {template.name}
                        {selectedTemplate === template.key && <Check size={13} color="var(--clh-primary)" />}
                      </span>
                      <span className="role-desc d-block">{template.description}</span>
                    </span>
                  </button>
                ))}
              </div>
            </SectionCard>

            <SectionCard title="Project definition">
              <div className="stack stack-3">
                <div>
                  <label className="form-label" htmlFor="name">
                    Project name<span className="required-mark">*</span>
                  </label>
                  <input id="name" className="form-control" {...register('name')} placeholder="e.g. Why are shampoo buyers not purchasing again?" />
                  {errors.name && <div className="field-error">{errors.name.message}</div>}
                </div>

                <div>
                  <label className="form-label" htmlFor="objective">
                    Research objective<span className="required-mark">*</span>
                  </label>
                  <textarea
                    id="objective"
                    className="form-control"
                    rows={3}
                    {...register('objective')}
                    placeholder="What do you want to understand, and what would change if you understood it?"
                  />
                  {errors.objective && <div className="field-error">{errors.objective.message}</div>}
                  <div className="form-text">
                    A good objective names the uncertainty. “Confirm customers think we are expensive” is a
                    conclusion, not a question.
                  </div>
                </div>

                <div>
                  <label className="form-label" htmlFor="description">
                    Context (optional)
                  </label>
                  <textarea id="description" className="form-control" rows={3} {...register('description')} />
                </div>

                <div className="section-grid grid-2" style={{ gap: 12 }}>
                  <div>
                    <label className="form-label" htmlFor="methodology">
                      Method
                    </label>
                    <input id="methodology" className="form-control" {...register('methodology')} />
                  </div>
                  <div>
                    <label className="form-label" htmlFor="owner_id">
                      Project owner
                    </label>
                    <select id="owner_id" className="form-select" {...register('owner_id')}>
                      <option value="">Assign to me</option>
                      {users.map((user) => (
                        <option key={user.id} value={user.id}>
                          {user.name} · {user.job_title}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="form-label" htmlFor="priority">
                      Priority
                    </label>
                    <select id="priority" className="form-select" {...register('priority')}>
                      {(['low', 'medium', 'high', 'critical'] as Priority[]).map((priority) => (
                        <option key={priority} value={priority}>
                          {titleCase(priority)}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="form-label" htmlFor="status">
                      Starting status
                    </label>
                    <select id="status" className="form-select" {...register('status')}>
                      {(['draft', 'planning', 'recruiting', 'in_progress'] as ProjectStatus[]).map((status) => (
                        <option key={status} value={status}>
                          {titleCase(status)}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="form-label" htmlFor="start_date">
                      Start date
                    </label>
                    <input id="start_date" type="date" className="form-control" {...register('start_date')} />
                  </div>
                  <div>
                    <label className="form-label" htmlFor="deadline">
                      Deadline
                    </label>
                    <input id="deadline" type="date" className="form-control" {...register('deadline')} />
                    {errors.deadline && <div className="field-error">{errors.deadline.message}</div>}
                  </div>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Research questions" subtitle="The specific uncertainties this project should reduce">
              <div className="stack stack-2">
                {questions.map((question, index) => (
                  <div key={index} className="d-flex gap-2">
                    <input
                      className="form-control"
                      value={question}
                      placeholder={index === 0 ? 'What happened after the first bottle was finished?' : 'Another question'}
                      onChange={(event) => {
                        const next = [...questions]
                        next[index] = event.target.value
                        setQuestions(next)
                      }}
                      aria-label={`Research question ${index + 1}`}
                    />
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      aria-label="Remove question"
                      onClick={() => setQuestions(questions.length === 1 ? [''] : questions.filter((_, i) => i !== index))}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm align-self-start"
                  onClick={() => setQuestions([...questions, ''])}
                >
                  <Plus size={13} /> Add question
                </button>
                <div className="form-text">
                  Questions are shown in the interview guide and stay attached to the project so findings can be traced
                  back to the uncertainty they addressed.
                </div>
              </div>
            </SectionCard>
          </div>

          <div className="stack stack-3">
            <SectionCard title="Business functions" subtitle="Who needs this answer?">
              <div className="stack stack-2">
                {BUSINESS_FUNCTIONS.map((fn) => (
                  <label key={fn} className="inline" style={{ gap: 8, fontSize: 13 }}>
                    <input
                      type="checkbox"
                      checked={businessFunctions.includes(fn)}
                      onChange={() => toggle('business_functions', fn)}
                    />
                    {BUSINESS_FUNCTION_LABELS[fn]}
                  </label>
                ))}
                {errors.business_functions && <div className="field-error">{errors.business_functions.message}</div>}
              </div>
            </SectionCard>

            <SectionCard title="Target segments" subtitle="Who is missing from the usual sample?">
              <div className="stack stack-2">
                {SEGMENTS.map((segment) => (
                  <label key={segment} className="inline" style={{ gap: 8, fontSize: 13 }}>
                    <input
                      type="checkbox"
                      checked={targetSegments.includes(segment)}
                      onChange={() => toggle('target_segments', segment)}
                    />
                    {SEGMENT_LABELS[segment]}
                  </label>
                ))}
                {errors.target_segments && <div className="field-error">{errors.target_segments.message}</div>}
              </div>
              <div className="form-text mt-2">
                The recruitment pipeline warns you when a chosen segment has no participants, so quietly interviewing
                repeat buyers cannot be presented as “what customers think”.
              </div>
            </SectionCard>

            <SectionCard title="Before you save">
              <Notice tone="neutral">
                Creating a project does not contact anyone. Invitations are recorded manually and labelled as
                simulated in this prototype.
              </Notice>
              {serverError && (
                <div className="mt-2">
                  <Notice tone="danger" title="The project could not be created">
                    {serverError}
                  </Notice>
                </div>
              )}
              <div className="stack stack-2 mt-3">
                <button type="submit" className="btn btn-primary" disabled={isSubmitting || mutation.isPending}>
                  {mutation.isPending ? 'Creating…' : 'Create research project'}
                </button>
                <Link to="/projects" className="btn btn-outline-secondary">
                  Cancel
                </Link>
              </div>
            </SectionCard>
          </div>
        </div>
      </form>
    </div>
  )
}

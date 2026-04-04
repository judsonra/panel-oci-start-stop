import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { TreeNode } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { StepsModule } from 'primeng/steps';
import { TreeModule } from 'primeng/tree';
import { ApiService } from '@/app/core/api.service';
import { ApiErrorResponse, GroupModel, GroupTreeCompartmentModel } from '@/app/core/models';

@Component({
    selector: 'app-group-form-page',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, ButtonModule, InputTextModule, MessageModule, StepsModule, TreeModule],
    template: `
        <section class="page-header">
            <div>
                <span class="section-kicker">Grupos</span>
                <h2>{{ editingGroupId() ? 'Editar grupo' : 'Novo grupo' }}</h2>
                <p>Defina o nome, escolha as instâncias na árvore por compartimento e revise antes de salvar.</p>
            </div>
        </section>

        @if (error()) {
            <p-message severity="error" [text]="error() || ''"></p-message>
        }

        @if (feedback()) {
            <p-message [severity]="feedbackSeverity()" [text]="feedback() || ''"></p-message>
        }

        <section class="wizard-shell">
            <p-steps [model]="stepItems" [activeIndex]="activeStep()" [readonly]="true"></p-steps>

            <div class="wizard-panel">
                @if (activeStep() === 0) {
                    <form class="form-panel" [formGroup]="form">
                        <label>
                            <span>Nome do grupo</span>
                            <input pInputText formControlName="name" placeholder="Ex.: Operação Financeira" />
                        </label>
                    </form>
                }

                @if (activeStep() === 1) {
                    <div class="groups-tree-panel">
                        <p-tree
                            [value]="treeNodes()"
                            selectionMode="checkbox"
                            [selection]="selectedTreeNodes()"
                            (selectionChange)="onSelectionChange($event)"
                        ></p-tree>
                    </div>
                }

                @if (activeStep() === 2) {
                    <section class="group-review-panel">
                        <article class="auto-register-summary-card">
                            <span>Grupo</span>
                            <strong>{{ form.controls.name.value }}</strong>
                        </article>

                        <div class="group-review-columns">
                            @for (instance of selectedInstances(); track instance.id) {
                                <div class="group-review-item">{{ instance.name }}</div>
                            }
                        </div>
                    </section>
                }
            </div>

            <div class="form-actions">
                <button pButton type="button" label="Cancelar" severity="secondary" [outlined]="true" (click)="cancel()"></button>
                @if (activeStep() > 0) {
                    <button pButton type="button" label="Voltar" severity="secondary" [outlined]="true" (click)="previousStep()"></button>
                }
                @if (activeStep() < 2) {
                    <button pButton type="button" label="Avançar" (click)="nextStep()" [disabled]="!canAdvance()"></button>
                } @else {
                    <button pButton type="button" label="Salvar grupo" icon="pi pi-save" (click)="save()" [disabled]="saving() || selectedInstances().length === 0"></button>
                }
            </div>
        </section>
    `
})
export class GroupFormPage implements OnInit {
    private readonly api = inject(ApiService);
    private readonly route = inject(ActivatedRoute);
    private readonly router = inject(Router);
    private readonly formBuilder = inject(FormBuilder);

    readonly editingGroupId = signal<string | null>(null);
    readonly loading = signal(false);
    readonly saving = signal(false);
    readonly error = signal<string | null>(null);
    readonly feedback = signal<string | null>(null);
    readonly feedbackSeverity = signal<'success' | 'error'>('success');
    readonly activeStep = signal(0);
    readonly groupTree = signal<GroupTreeCompartmentModel[]>([]);
    readonly selectedTreeNodes = signal<TreeNode[]>([]);
    readonly stepItems = [
        { label: 'Nome do grupo' },
        { label: 'Escolher instâncias' },
        { label: 'Verificação' }
    ];
    readonly treeNodes = computed<TreeNode[]>(() =>
        this.groupTree().map((compartment) => ({
            key: `compartment-${compartment.id}`,
            label: compartment.name,
            selectable: true,
            children: compartment.instances.map((instance) => ({
                key: `instance-${instance.id}`,
                label: instance.name,
                data: instance,
                leaf: true
            }))
        }))
    );
    readonly selectedInstances = computed(() => {
        return this.collectSelectedInstances(this.selectedTreeNodes());
    });

    readonly form = this.formBuilder.nonNullable.group({
        name: ['', [Validators.required, Validators.maxLength(120)]]
    });

    ngOnInit(): void {
        const groupId = this.route.snapshot.paramMap.get('groupId');
        this.editingGroupId.set(groupId);
        this.loading.set(true);
        this.error.set(null);
        this.api
            .getGroupTree()
            .subscribe({
                next: (tree) => {
                    this.groupTree.set(tree);
                    if (!groupId) {
                        this.loading.set(false);
                        return;
                    }
                    this.api.getGroup(groupId).subscribe({
                        next: (group) => {
                            this.applyGroup(group);
                            this.loading.set(false);
                        },
                        error: () => {
                            this.error.set('Não foi possível carregar os dados do grupo.');
                            this.loading.set(false);
                        }
                    });
                },
                error: () => {
                    this.error.set('Não foi possível carregar os dados do grupo.');
                    this.loading.set(false);
                }
            });
    }

    onSelectionChange(value: TreeNode | TreeNode[] | null | undefined): void {
        if (!value) {
            this.selectedTreeNodes.set([]);
            return;
        }

        this.selectedTreeNodes.set(Array.isArray(value) ? value : [value]);
    }

    canAdvance(): boolean {
        if (this.activeStep() === 0) {
            return this.form.valid;
        }
        if (this.activeStep() === 1) {
            return this.selectedInstances().length > 0;
        }
        return true;
    }

    nextStep(): void {
        if (!this.canAdvance()) {
            this.form.markAllAsTouched();
            return;
        }
        this.activeStep.set(Math.min(this.activeStep() + 1, 2));
    }

    previousStep(): void {
        this.activeStep.set(Math.max(this.activeStep() - 1, 0));
    }

    cancel(): void {
        void this.router.navigate(['/groups']);
    }

    save(): void {
        if (this.form.invalid || this.selectedInstances().length === 0) {
            this.form.markAllAsTouched();
            return;
        }

        const payload = {
            name: this.form.controls.name.value.trim(),
            instance_ids: this.selectedInstances().map((instance) => instance.id)
        };
        const groupId = this.editingGroupId();
        const request$ = groupId ? this.api.updateGroup(groupId, payload) : this.api.createGroup(payload);

        this.saving.set(true);
        this.error.set(null);
        request$.subscribe({
            next: () => {
                this.saving.set(false);
                void this.router.navigate(['/groups'], {
                    state: {
                        feedback: groupId ? 'Grupo atualizado com sucesso.' : 'Grupo criado com sucesso.'
                    }
                });
            },
            error: (response: { error?: ApiErrorResponse }) => {
                this.saving.set(false);
                this.feedbackSeverity.set('error');
                this.feedback.set(response.error?.detail ?? 'Não foi possível salvar o grupo.');
            }
        });
    }

    private applyGroup(group: GroupModel): void {
        this.form.patchValue({ name: group.name });
        const selectedIds = new Set(group.instances.map((instance) => instance.id));
        const selectedNodes = this.treeNodes()
            .flatMap((compartment) => compartment.children ?? [])
            .filter((node) => {
                const key = typeof node.key === 'string' ? node.key : '';
                return key.startsWith('instance-') && selectedIds.has(key.replace('instance-', ''));
            });
        this.selectedTreeNodes.set(selectedNodes);
    }

    private collectSelectedInstances(nodes: TreeNode[]): { id: string; name: string; ocid: string }[] {
        const seen = new Map<string, { id: string; name: string; ocid: string }>();
        const visit = (node: TreeNode | undefined) => {
            if (!node) {
                return;
            }

            const data = node.data as { id?: string; name?: string; ocid?: string } | undefined;
            if (data?.id && data.name && data.ocid) {
                seen.set(data.id, { id: data.id, name: data.name, ocid: data.ocid });
            }

            for (const child of node.children ?? []) {
                visit(child);
            }
        };

        for (const node of nodes) {
            visit(node);
        }

        return [...seen.values()].sort((left, right) => left.name.localeCompare(right.name, 'pt-BR'));
    }
}

///
/// Copyright © 2016-2026 The Thingsboard Authors
///
/// Licensed under the Apache License, Version 2.0 (the "License");
/// you may not use this file except in compliance with the License.
/// You may obtain a copy of the License at
///
///     http://www.apache.org/licenses/LICENSE-2.0
///
/// Unless required by applicable law or agreed to in writing, software
/// distributed under the License is distributed on an "AS IS" BASIS,
/// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
/// See the License for the specific language governing permissions and
/// limitations under the License.
///

import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { Store } from '@ngrx/store';
import { AppState } from '@core/core.state';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { DeviceService } from '@core/http/device.service';
import { AssetService } from '@core/http/asset.service';
import { EntityRelationService } from '@core/http/entity-relation.service';
import { DialogComponent } from '@shared/components/dialog.component';
import { Router } from '@angular/router';
import { ClaimResult, ClaimResponse } from '@shared/models/device.models';
import { PageLink } from '@shared/models/page/page-link';
import { AssetInfo } from '@shared/models/asset.models';
import { ActionNotificationShow } from '@core/notification/notification.actions';
import { EntityRelation, RelationTypeGroup } from '@shared/models/relation.models';
import { EntityType } from '@shared/models/entity-type.models';

export interface ClaimHubDialogData {
  defaultRoomId?: string;
}

@Component({
  selector: 'tb-claim-hub-dialog',
  templateUrl: './claim-hub-dialog.component.html',
  styleUrls: ['./claim-hub-dialog.component.scss'],
  standalone: false
})
export class ClaimHubDialogComponent extends DialogComponent<ClaimHubDialogComponent, ClaimResult> implements OnInit {

  claimHubForm: FormGroup;
  rooms: AssetInfo[] = [];
  loading = false;
  errorMessage = '';

  constructor(
    protected store: Store<AppState>,
    protected router: Router,
    @Inject(MAT_DIALOG_DATA) public data: ClaimHubDialogData,
    public dialogRef: MatDialogRef<ClaimHubDialogComponent, ClaimResult>,
    private fb: FormBuilder,
    private deviceService: DeviceService,
    private assetService: AssetService,
    private relationService: EntityRelationService
  ) {
    super(store, router, dialogRef);
  }

  ngOnInit(): void {
    this.claimHubForm = this.fb.group({
      deviceName: ['', [Validators.required, Validators.pattern(/^[a-zA-Z0-9_\-]+$/)]],
      secretKey: ['', [Validators.required]],
      roomAssetId: [this.data?.defaultRoomId || '']
    });

    this.loadRooms();
  }

  private loadRooms(): void {
    const pageLink = new PageLink(50);
    this.assetService.getCustomerAssetInfos(pageLink, '').subscribe({
      next: (pageData) => {
        this.rooms = pageData.data || [];
      },
      error: () => {
        this.rooms = [];
      }
    });
  }

  submit(): void {
    if (this.claimHubForm.invalid) {
      return;
    }

    this.loading = true;
    this.errorMessage = '';

    const deviceName = this.claimHubForm.get('deviceName').value.trim();
    const secretKey = this.claimHubForm.get('secretKey').value.trim();
    const roomAssetId = this.claimHubForm.get('roomAssetId').value;

    this.deviceService.claimDevice(deviceName, { secretKey }).subscribe({
      next: (result: ClaimResult) => {
        if (result.response === ClaimResponse.SUCCESS) {
          // If a room was chosen, create relationship between Room Asset and Hub Device
          if (roomAssetId && result.device?.id) {
            const relation: EntityRelation = {
              from: { id: roomAssetId, entityType: EntityType.ASSET },
              to: result.device.id,
              type: 'Contains',
              typeGroup: RelationTypeGroup.COMMON
            };
            this.relationService.saveRelation(relation).subscribe({
              next: () => {
                this.onClaimSuccess(result);
              },
              error: () => {
                this.onClaimSuccess(result);
              }
            });
          } else {
            this.onClaimSuccess(result);
          }
        } else if (result.response === ClaimResponse.CLAIMED) {
          this.loading = false;
          this.errorMessage = 'هذا الموزع مرتبط بحساب آخر بالفعل.';
        } else {
          this.loading = false;
          this.errorMessage = 'فشل التحقق من بيانات الموزع. يرجى التأكد من الرقم التسلسلي والرمز السري.';
        }
      },
      error: (err) => {
        this.loading = false;
        this.errorMessage = err?.error?.message || 'تعذر الاتصال بالسيرفر للربط.';
      }
    });
  }

  private onClaimSuccess(result: ClaimResult): void {
    this.loading = false;
    this.store.dispatch(new ActionNotificationShow({
      message: 'تم ربط موزع UNIQ بنجاح بمساحتك الذكية!',
      type: 'success',
      duration: 3500
    }));
    this.dialogRef.close(result);
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}

//
// Copyright 2021 Autodesk
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
#ifndef USDUFE_USD_POINT_INSTANCE_ORIENTATION_MODIFIER_H
#define USDUFE_USD_POINT_INSTANCE_ORIENTATION_MODIFIER_H

#include <usdUfe/base/api.h>
#include <usdUfe/ufe/trf/UsdPointInstanceModifierBase.h>

#include <pxr/base/gf/quath.h>
#include <pxr/pxr.h>
#include <pxr/usd/usd/attribute.h>
#include <pxr/usd/usd/prim.h>

#include <ufe/types.h>

namespace USDUFE_NS_DEF {

/// Modifier specialization for accessing and modifying a point instance's
/// orientation.
///
class USDUFE_PUBLIC UsdPointInstanceOrientationModifier
    : public UsdPointInstanceModifierBase<Ufe::Vector3d, PXR_NS::GfQuath>
{
public:
    UsdPointInstanceOrientationModifier()
        : UsdPointInstanceModifierBase<Ufe::Vector3d, PXR_NS::GfQuath>()
    {
    }

    PXR_NS::GfQuath convertValueToUsd(const Ufe::Vector3d& ufeValue) const override;

    Ufe::Vector3d convertValueToUfe(const PXR_NS::GfQuath& usdValue) const override;

    PXR_NS::GfQuath getDefaultUsdValue() const override { return PXR_NS::GfQuath::GetIdentity(); }

    Batches& batches() override;

    PXR_NS::UsdAttribute getAttribute() const override;

protected:
    PXR_NS::UsdAttribute _createAttribute() override;
};

} // namespace USDUFE_NS_DEF

#endif
